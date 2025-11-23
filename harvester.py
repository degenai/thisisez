import json
import time
import random
import os
import requests
from datetime import datetime
import google.generativeai as genai
from dotenv import load_dotenv

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

def fetch_catalog():
    print(f"[*] Scanning /{BOARD}/ catalog...")
    try:
        response = requests.get(CATALOG_URL)
        if response.status_code == 200:
            data = response.json()
            threads = []
            for page in data:
                for thread in page['threads']:
                    # Filter for "high signal" threads (e.g., > 5 replies) to save tokens
                    if thread.get('replies', 0) > 5:
                        threads.append(thread)
            print(f"[+] Found {len(threads)} active threads.")
            return threads
        else:
            print(f"[!] Error fetching catalog: {response.status_code}")
            return []
    except Exception as e:
        print(f"[!] Connection failed: {e}")
        return []

def distill_thread(thread):
    # If no API key, return mock data
    if not model:
        return mock_distill(thread)

    print(f"[*] Distilling Thread {thread['no']}: {thread.get('sub', thread.get('com', 'No Subject'))[:30]}...")
    
    # Prepare content for Gemini
    subject = thread.get('sub', '')
    comment = thread.get('com', '')
    
    # Clean HTML from comment (basic)
    comment = comment.replace('<br>', '\n').replace('&gt;', '>')
    
    prompt = f"""
    Analyze this 4chan /biz/ thread.
    Subject: {subject}
    OP Post: {comment}
    
    Task:
    1. Identify the "Gestalt" or Metanarrative. What is the underlying psychological or market truth here?
    2. Rate the sentiment on these 5 axes (0-100):
       - GREED (FOMO, Bullishness)
       - FEAR (Panic, Doom)
       - SCHIZO (Conspiracy, Esoteric)
       - IQ (High level analysis, Signal)
       - SHILL (Artificial marketing, Bot behavior)
    3. Extract 3-5 key tags/keywords.
    4. Identify specific "Assets" mentioned (Coins, Stocks, Commodities, or Concepts).
       - Name: The name of the asset (e.g., "Gold", "Solana", "The Dollar").
       - Narrative: What is being said about THIS specific asset? (1 sentence).
       - Sentiment: BULLISH, BEARISH, or NEUTRAL.
    5. Subject Line Check:
       - If the provided 'Subject' is empty, generic (e.g., "Thread", "General", "/biz/"), or missing, GENERATE a short, punchy, 4chan-style subject line based on the content.
       - If the provided 'Subject' is good, keep it.

    Output JSON ONLY:
    {{
        "subject": "The final subject line (original or generated)",
        "is_generated_subject": true/false,
        "gestalt_summary": "METANARRATIVE: [Your 2 sentence summary]",
        "radar": {{ "GREED": 0, "FEAR": 0, "SCHIZO": 0, "IQ": 0, "SHILL": 0 }},
        "keywords": ["tag1", "tag2"],
        "assets": [
            {{ "name": "Asset Name", "narrative": "Specific narrative...", "sentiment": "BULLISH" }}
        ]
    }}
    """

    try:
        response = model.generate_content(prompt)
        # Clean response to ensure valid JSON
        text = response.text.replace('```json', '').replace('```', '').strip()
        analysis = json.loads(text)
        
        return {
            "id": f"thread_{thread['no']}",
            "timestamp": datetime.now().isoformat(),
            "subject": analysis.get('subject', subject or "No Subject"),
            "is_generated_subject": analysis.get('is_generated_subject', False),
            "url": f"https://boards.4channel.org/{BOARD}/thread/{thread['no']}",
            "gestalt_summary": analysis['gestalt_summary'],
            "radar": analysis['radar'],
            "keywords": analysis['keywords'],
            "assets": analysis.get('assets', [])
        }
    except Exception as e:
        print(f"[!] Distillation failed: {e}")
        return mock_distill(thread)

def mock_distill(thread):
    # Fallback for testing or no API key
    return {
        "id": f"thread_{thread['no']}",
        "timestamp": datetime.now().isoformat(),
        "subject": thread.get('sub', 'Unknown Thread'),
        "url": f"https://boards.4channel.org/{BOARD}/thread/{thread['no']}",
        "gestalt_summary": "METANARRATIVE: [MOCK] The hivemind is vibrating with simulated anxiety.",
        "radar": {
            "GREED": random.randint(0, 100),
            "FEAR": random.randint(0, 100),
            "SCHIZO": random.randint(0, 100),
            "IQ": random.randint(0, 100),
            "SHILL": random.randint(0, 100)
        },
        "keywords": ["MOCK", "DATA", "TEST"]
    }

def export_gestalt(data):
    print(f"[*] Exporting {len(data)} Gestalts to {OUTPUT_FILE}...")
    with open(OUTPUT_FILE, 'w') as f:
        json.dump(data, f, indent=2)
    print("[+] Export Complete.")

def main():
    print("=== AURA FARMER HARVESTER v2.0 ===")
    threads = fetch_catalog()
    
    # Limit to top 5 threads for testing to save API credits/time
    # In production, this would be a loop or user selection
    target_threads = threads[:3] 
    
    gestalts = []
    for thread in target_threads:
        gestalt = distill_thread(thread)
        if gestalt:
            gestalts.append(gestalt)
        time.sleep(1) # Rate limit politeness
        
    export_gestalt(gestalts)

if __name__ == "__main__":
    main()
