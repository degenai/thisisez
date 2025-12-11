import json
import time
import random
import os
import requests
from datetime import datetime
import google.generativeai as genai
from dotenv import load_dotenv
from PIL import Image
import io

# Compatibility Patch for Python < 3.10
import sys
if sys.version_info < (3, 10):
    try:
        import importlib_metadata
        import importlib.metadata
        if not hasattr(importlib.metadata, 'packages_distributions'):
            importlib.metadata.packages_distributions = importlib_metadata.packages_distributions
    except ImportError:
        pass # importlib_metadata not installed

# Load Environment Variables
load_dotenv()
API_KEY = os.getenv("GEMINI_API_KEY")

# Configuration
BOARD = "biz"
CATALOG_URL = f"https://a.4cdn.org/{BOARD}/catalog.json"
CDN_URL = f"https://i.4cdn.org/{BOARD}/"
OUTPUT_FILE = "gestalt_export.json"

# Setup Gemini
if API_KEY:
    genai.configure(api_key=API_KEY)
    model = genai.GenerativeModel('gemini-2.5-flash')
    print("[!] GEMINI SYSTEM: ONLINE (MODEL: gemini-2.5-flash)")
else:
    print("[!] WARNING: NO API KEY FOUND. RUNNING IN LIMITED MODE.")
    model = None

def get_catalog(board_name="biz", limit=0):
    print(f"[*] Scanning /{board_name}/ catalog...")
    url = f"https://a.4cdn.org/{board_name}/catalog.json"
    try:
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            threads = []
            for page in data:
                for thread in page['threads']:
                    # Filter for "high signal" threads (e.g., > 5 replies) to save tokens
                    if thread.get('replies', 0) > 5:
                        threads.append(thread)
            
            total_found = len(threads)
            if limit > 0:
                threads = threads[:limit]
                print(f"[+] Found {total_found} active threads. Limiting to {limit}.")
            else:
                print(f"[+] Found {total_found} active threads.")
                
            return threads
        else:
            print(f"[!] Error fetching catalog: {response.status_code}")
            return []
    except Exception as e:
        print(f"[!] Connection failed: {e}")
        return []

def fetch_image(tim, ext):
    """Fetches and processes an image from 4chan CDN."""
    try:
        url = f"{CDN_URL}{tim}{ext}"
        print(f"[*] Fetching image: {url}")
        resp = requests.get(url, stream=True)
        if resp.status_code == 200:
            img = Image.open(io.BytesIO(resp.content))
            return img
        return None
    except Exception as e:
        print(f"[!] Image fetch failed: {e}")
        return None

def distill_thread(thread, model_instance=None):
    # Use passed model or global model
    active_model = model_instance if model_instance else model

    # If no API key/model, return mock data
    if not active_model:
        return mock_distill(thread), "NO_MODEL"

    print(f"[*] Distilling Thread {thread['no']}: {thread.get('sub', thread.get('com', 'No Subject'))[:50]}...")
    
    # Prepare content for Gemini
    subject = thread.get('sub', '')
    comment = thread.get('com', '')
    
    # Clean HTML from comment (basic)
    comment = comment.replace('<br>', '\n').replace('&gt;', '>')
    
    # Fetch full thread with replies
    try:
        thread_url = f"https://a.4cdn.org/{BOARD}/thread/{thread['no']}.json"
        full_thread_resp = requests.get(thread_url)
        if full_thread_resp.status_code == 200:
            posts = full_thread_resp.json().get('posts', [])
            # Skip OP (already have it) and take up to 50 replies to fit context
            replies_text = "\n---\n".join(
                [p.get('com', '').replace('<br>', '\n').replace('&gt;', '>') 
                 for p in posts[1:51] if 'com' in p]
            )
        else:
            replies_text = "[Could not fetch replies]"
    except Exception as e:
        replies_text = f"[Error fetching replies: {e}]"

    # Fetch Image if available
    image_data = None
    if 'tim' in thread and 'ext' in thread:
        image_data = fetch_image(thread['tim'], thread['ext'])

    prompt = f"""
    Analyze this 4chan /biz/ thread.
    Subject: {subject}
    OP Post: {comment}
    
    Replies (Sample):
    {replies_text}
    
    [IMAGE CONTEXT]: An image is attached to the OP. 
    - If it is a CHART, analyze the trend (Bullish/Bearish).
    - If it is a MEME/SCREENSHOT, analyze the sentiment/mood.
    - If it is generic, weight it lightly but do not ignore it.
    
    Task:
    1. Identify the "Gestalt" or Metanarrative. What is the underlying psychological or market truth here?
    2. Rate the sentiment on these 5 axes (0-100):
       - GREED (FOMO, Bullishness)
       - FEAR (Panic, Doom)
       - SCHIZO (Conspiracy, Esoteric)
       - IQ (High level analysis, Signal)
       - SHILL (Artificial marketing, Bot behavior)
       - CHUCKLE_FACTOR (Humor, Irony, Kek)
    3. Extract 3-5 key tags/keywords.
    4. Identify specific "Assets" mentioned (Coins, Stocks, Commodities, or Concepts).
       - Name: The name of the asset (e.g., "Gold", "Solana", "The Dollar").
       - Narrative: What is being said about THIS specific asset? (1 sentence).
       - Sentiment: BULLISH, BEARISH, or NEUTRAL.
       - CRITICAL NUANCE: Distinguish between the SUBJECT of the news and the TARGET of the sentiment.
         Example: "China tariffs will crush the US economy."
         -> Asset: "China" -> Sentiment: NEUTRAL (They are the actor/subject).
         -> Asset: "US Economy" -> Sentiment: BEARISH (They are the target/victim).
    5. Subject Line Check:
       - If the provided 'Subject' is empty, generic (e.g., "Thread", "General", "/biz/"), or missing, GENERATE a short, punchy, 4chan-style subject line based on the content.
       - If the provided 'Subject' is good, keep it.
    6. Top Quote Extraction:
       - Identify the single most insightful, funny, or representative quote (or short 2-way exchange) from the thread.
       - Prioritize passages with a high composite score of (CHUCKLE_FACTOR + IQ).
       - Keep it raw but readable.
    7. Image Analysis (If applicable):
       - If an image was provided, provide a 1-sentence description/analysis of it.
       - If no image, leave empty.

    Output JSON ONLY:
    {{
        "subject": "The final subject line (original or generated)",
        "is_generated_subject": true/false,
        "gestalt_summary": "METANARRATIVE: [Your 2 sentence summary]",
        "radar": {{ "GREED": 0, "FEAR": 0, "SCHIZO": 0, "IQ": 0, "SHILL": 0, "CHUCKLE_FACTOR": 0 }},
        "keywords": ["tag1", "tag2"],
        "top_quote": "The quote text here...",
        "image_analysis": "Description of the image...",
        "assets": [
            {{ "name": "Asset Name", "narrative": "Specific narrative...", "sentiment": "BULLISH" }}
        ]
    }}
    """

    for attempt in range(3):
        try:
            content_payload = [prompt]
            if image_data:
                content_payload.append(image_data)

            response = active_model.generate_content(
                content_payload,
                generation_config={"response_mime_type": "application/json"},
                safety_settings={
                    "HARM_CATEGORY_HARASSMENT": "BLOCK_NONE",
                    "HARM_CATEGORY_HATE_SPEECH": "BLOCK_NONE",
                    "HARM_CATEGORY_SEXUALLY_EXPLICIT": "BLOCK_NONE",
                    "HARM_CATEGORY_DANGEROUS_CONTENT": "BLOCK_NONE",
                }
            )
            # Clean response to ensure valid JSON
            text = response.text.replace('```json', '').replace('```', '').strip()
            analysis = json.loads(text)
            
            return {
                "id": f"thread_{thread['no']}",
                "timestamp": datetime.now().isoformat(),
                "subject": analysis.get('subject', subject or "No Subject"),
                "is_generated_subject": analysis.get('is_generated_subject', False),
                "url": f"https://boards.4channel.org/{BOARD}/thread/{thread['no']}",
                "replies": thread.get('replies', 0),
                "gestalt_summary": analysis['gestalt_summary'],
                "radar": analysis['radar'],
                "keywords": analysis['keywords'],
                "top_quote": analysis.get('top_quote', ''),
                "image_analysis": analysis.get('image_analysis', ''),
                "assets": analysis.get('assets', [])
            }, None
        except Exception as e:
            error_msg = str(e)
            if "PROHIBITED_CONTENT" in error_msg or "response.parts" in error_msg:
                print(f"[!] Thread {thread['no']} BLOCKED by safety filters. Skipping.")
                return None, "SAFETY_FILTER" # Skip this thread entirely
            
            print(f"[!] Distillation failed (Attempt {attempt+1}/3): {e}")
            time.sleep(1)

    print(f"[!] All attempts failed for Thread {thread['no']}. Using Mock.")
    return mock_distill(thread), "MOCK_USED"

def mock_distill(thread):
    # Fallback for testing or no API key
    return {
        "id": f"thread_{thread['no']}",
        "timestamp": datetime.now().isoformat(),
        "subject": thread.get('sub', 'Unknown Thread'),
        "url": f"https://boards.4channel.org/{BOARD}/thread/{thread['no']}",
        "replies": thread.get('replies', random.randint(5, 200)),
        "gestalt_summary": "METANARRATIVE: [MOCK] The hivemind is vibrating with simulated anxiety.",
        "radar": {
            "GREED": random.randint(0, 100),
            "FEAR": random.randint(0, 100),
            "SCHIZO": random.randint(0, 100),
            "IQ": random.randint(0, 100),
            "SHILL": random.randint(0, 100),
            "CHUCKLE_FACTOR": random.randint(0, 100)
        },
        "keywords": ["MOCK", "DATA", "TEST"],
        "top_quote": "This is a mock quote for testing purposes.",
        "image_analysis": "Mock image analysis.",
        "assets": [
            {"name": "BTC", "narrative": "Mock Bitcoin narrative", "sentiment": "BULLISH"},
            {"name": "LINK", "narrative": "Mock Chainlink narrative", "sentiment": "NEUTRAL"}
        ]
    }

def export_gestalt(data):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"gestalt_export_{timestamp}.json"
    
    print(f"[*] Exporting {len(data)} Gestalts to {filename}...")
    with open(filename, 'w') as f:
        json.dump(data, f, indent=2)
        
    # Update manifest file
    manifest = {"latest": filename}
    with open("latest_manifest.json", 'w') as f:
        json.dump(manifest, f, indent=2)
        
    print(f"[+] Export Complete. Saved to {filename} and updated latest_manifest.json")

    # --- ARCHIVING LOGIC ---
    try:
        # Ensure archive directory exists
        archive_dir = "scanexports"
        if not os.path.exists(archive_dir):
            os.makedirs(archive_dir)
            print(f"[*] Created archive directory: {archive_dir}")

        # List all gestalt exports in root
        files = [f for f in os.listdir('.') if f.startswith('gestalt_export_') and f.endswith('.json')]
        
        # Sort by modification time (newest first)
        # We use modification time as a proxy for creation time/filename timestamp order
        files.sort(key=lambda x: os.path.getmtime(x), reverse=True)
        
        # Keep top 5, move the rest
        keep_count = 5
        if len(files) > keep_count:
            to_archive = files[keep_count:]
            print(f"[*] Archiving {len(to_archive)} old export(s) to {archive_dir}/...")
            
            for f in to_archive:
                src = f
                dst = os.path.join(archive_dir, f)
                try:
                    os.rename(src, dst)
                    print(f"    -> Moved {src}")
                except Exception as e:
                    print(f"    [!] Failed to move {src}: {e}")
        else:
            print(f"[*] {len(files)} exports found. No archiving needed (Limit: {keep_count}).")
            
    except Exception as e:
        print(f"[!] Archiving process failed: {e}")

def main(limit=0):
    print("=== AURA FARMER HARVESTER v2.0 ===")
    threads = get_catalog(BOARD, limit)
    
    # Process all threads found (filtered by reply count in get_catalog)
    target_threads = threads 
    
    gestalts = []
    total_assets = 0
    skipped_count = 0
    skip_reasons = {}
    
    for i, thread in enumerate(target_threads):
        gestalt, skip_reason = distill_thread(thread, model)
        
        if skip_reason and skip_reason != "MOCK_USED":
            skipped_count += 1
            skip_reasons[skip_reason] = skip_reasons.get(skip_reason, 0) + 1
            continue
            
        if gestalt:
            gestalts.append(gestalt)
            asset_count = len(gestalt.get('assets', []))
            total_assets += asset_count
            
            # Mini-Report every 5 threads
            if (i + 1) % 5 == 0:
                print(f"\n--- [MINI-REPORT: {i+1}/{len(target_threads)}] ---")
                print(f"Subject: {gestalt['subject'][:60]}")
                print(f"Quote: \"{gestalt.get('top_quote', '')[:100]}...\"")
                if gestalt.get('image_analysis'):
                    print(f"Img: {gestalt['image_analysis'][:100]}...")
                print(f"Radar: G:{gestalt['radar']['GREED']} F:{gestalt['radar']['FEAR']} KEK:{gestalt['radar']['CHUCKLE_FACTOR']}")
                print("-----------------------------------\n")
                
        time.sleep(1) # Rate limit politeness
        
    print(f"\n=== CYCLE COMPLETE ===")
    print(f"Threads Processed: {len(gestalts)}")
    print(f"Threads Skipped: {skipped_count}")
    if skipped_count > 0:
        print(f"Skip Reasons: {skip_reasons}")
    print(f"Total Assets Extracted: {total_assets}")
    print(f"======================")
        
    export_gestalt(gestalts)
    
    # Trigger Dashboard Aggregation
    try:
        import consolidator
        print("[*] Triggering Full Consolidation (Cleaning + LLM + Aggregation)...")
        consolidator.consolidate()
    except Exception as e:
        print(f"[!] Aggregation failed: {e}")

if __name__ == "__main__":
    main()
