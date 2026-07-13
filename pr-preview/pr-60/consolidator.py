import sys
import os
import json
import re
from datetime import datetime

# Compatibility Patch for Python < 3.10
# MUST BE RUN BEFORE OTHER IMPORTS
if sys.version_info < (3, 10):
    try:
        import importlib_metadata
        import importlib.metadata
        if not hasattr(importlib.metadata, 'packages_distributions'):
            importlib.metadata.packages_distributions = importlib_metadata.packages_distributions
    except ImportError:
        pass # importlib_metadata not installed

import google.generativeai as genai
from dotenv import load_dotenv

# Load Environment Variables
load_dotenv()
API_KEY = os.getenv("GEMINI_API_KEY")

# Configuration
INPUT_FILE = "gestalt_export.json"
OUTPUT_FILE = "gestalt_export.json"

# Setup Gemini
# Model configuration - easy to update when new models release
MODEL_FLASH = 'gemini-2.5-flash'  # Fast model for bulk operations (dedup, metatheses)
MODEL_PRO = 'gemini-3-pro-preview'  # Pro model for grand metanarrative (best reasoning)

if API_KEY:
    genai.configure(api_key=API_KEY)
    model = genai.GenerativeModel(MODEL_FLASH)
    model_pro = genai.GenerativeModel(MODEL_PRO)
else:
    print("[!] ERROR: NO API KEY FOUND.")
    model = None
    model_pro = None

def load_data():
    """
    Loads gestalt data from the latest timestamped JSON.
    Handles both old format (array) and new unified format (object with threads/dashboard).
    Returns: (threads_list, full_data_object, filename)
    """
    # 1. Try to read manifest
    filename = INPUT_FILE # Default fallback
    if os.path.exists("latest_manifest.json"):
        try:
            with open("latest_manifest.json", 'r') as f:
                manifest = json.load(f)
                filename = manifest.get("latest", INPUT_FILE)
                print(f"[*] Loaded manifest. Target file: {filename}")
        except Exception as e:
            print(f"[!] Error reading manifest: {e}")
    
    # 2. Load the file
    if not os.path.exists(filename):
        print(f"[!] Error: {filename} not found.")
        return None, None, None
        
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            raw_data = json.load(f)
        
        # Handle both old format (array) and new unified format (object)
        if isinstance(raw_data, list):
            # Old format: just an array of threads - convert to unified
            print(f"[*] Converting old format to unified format...")
            unified_data = {"threads": raw_data, "dashboard": None}
            threads = raw_data
        else:
            # New unified format
            unified_data = raw_data
            threads = raw_data.get("threads", [])
        
        return threads, unified_data, filename
    except Exception as e:
        print(f"[!] Error loading data: {e}")
        return None, None, None

def clean_name(name):
    """
    Deterministic cleanup:
    1. Strip whitespace.
    2. Remove parenthetical tickers (e.g. "Chainlink (LINK)" -> "Chainlink").
    """
    name = name.strip()
    # Regex to remove any parenthetical suffix at the end
    # Matches " (BTC)", " ($LINK)", " (LINK token)", etc.
    name = re.sub(r'\s*\([^)]+\)$', '', name)
    
    # Load Canonical Assets (Lazy load or cached)
    # For simplicity, we load it here. In production, cache this.
    try:
        if os.path.exists("canonical_assets.json"):
            with open("canonical_assets.json", 'r') as f:
                aliases = json.load(f)
        else:
            aliases = {}
    except Exception as e:
        print(f"[!] Error loading canonical assets: {e}")
        aliases = {}
    
    upper_name = name.upper()
    if upper_name in aliases:
        return aliases[upper_name]
        
    return name

def pre_process_data(data):
    """
    Applies deterministic cleaning to all assets before LLM processing.
    """
    count = 0
    for entry in data:
        for asset in entry.get('assets', []):
            original = asset['name']
            cleaned = clean_name(original)
            if cleaned != original:
                asset['name'] = cleaned
                count += 1
    if count > 0:
        print(f"[*] Pre-processed {count} assets (stripped tickers/whitespace).")
    return data

def get_unique_assets(data):
    assets = set()
    for entry in data:
        for asset in entry.get('assets', []):
            assets.add(asset['name'])
    return list(assets)

def generate_mapping(assets):
    if not model:
        return {}
    
    print(f"[*] Analyzing {len(assets)} unique assets for duplicates...")
    
    # Batching to avoid timeouts
    BATCH_SIZE = 100
    all_mappings = {}
    
    for i in range(0, len(assets), BATCH_SIZE):
        batch = assets[i:i+BATCH_SIZE]
        print(f"    > Processing batch {i//BATCH_SIZE + 1}/{(len(assets)-1)//BATCH_SIZE + 1} ({len(batch)} assets)...")
        
        prompt = f"""
        You are a data cleaner for a financial sentiment analysis tool focused on 4chan /biz/ and similar communities.
        Below is a list of asset names extracted from discussions.
        
        Your task is to identify STRICT SYNONYMS and map them to a single CANONICAL name.
        
        IMPORTANT CONTEXT:
        - "Assets" are NOT just stocks or cryptos. They can be:
          - People (e.g. "Michael Saylor", "Jerome Powell").
          - Concepts (e.g. "Housing Market", "Inflation", "The Fed").
          - Commodities (e.g. "Gold", "Silver").
          - Memes/Narratives (e.g. "Wagmi", "McDonalds application").
        
        Rules:
        1. Map Tickers to Full Names (e.g. "ETH" -> "Ethereum", "BTC" -> "Bitcoin").
        2. Map Typos/Variations to Canonical (e.g. "Chainlink (LINK)" -> "Chainlink", "LINK" -> "Chainlink").
        3. Group obvious synonyms (e.g. "Nvidia", "NVDA" -> "Nvidia").
        4. ALWAYS strip parenthetical tickers (e.g. "Asset (TICKER)" -> "Asset").
        
        NEGATIVE CONSTRAINTS (CRITICAL):
        - Do NOT merge specific products into parent companies if the product is a distinct asset class.
          (e.g. "iPhone" != "Apple", "GeForce" != "Nvidia").
        - Do NOT merge distinct economic concepts.
          (e.g. "Debt" != "Economy", "Inflation" != "Economy").
        - Do NOT merge distinct coins just because they are in the same ecosystem.
          (e.g. "Shiba Inu" != "Dogecoin").
        - Do NOT merge distinct regional markets.
          (e.g. "China Real Estate" != "Real Estate", "US Housing" != "Real Estate").
        - If in doubt, KEEP IT SEPARATE.
        
        Return ONLY a JSON object: {{"Synonym": "Canonical Name", ...}}
        
        Asset List:
        {json.dumps(batch)}
        """
        
        try:
            response = model.generate_content(prompt)
            text = response.text.strip()
            # Cleanup markdown code blocks if present
            if text.startswith("```json"):
                text = text[7:-3]
            elif text.startswith("```"):
                text = text[3:-3]
                
            batch_mapping = json.loads(text)
            all_mappings.update(batch_mapping)
        except Exception as e:
            print(f"[!] Error generating mapping for batch: {e}")
            # print(f"[!] Raw response: {text}")
            continue

    return all_mappings

def apply_mapping(data, mapping):
    count = 0
    for entry in data:
        for asset in entry.get('assets', []):
            original_name = asset['name']
            if original_name in mapping:
                asset['name'] = mapping[original_name]
                count += 1
    print(f"[*] Consolidated {count} asset references.")
    return data

def consolidate():
    print("=== ASSET CONSOLIDATOR ===")
    threads, unified_data, filename = load_data()
    if not threads:
        return
    
    # 1. Deterministic Pre-processing
    threads = pre_process_data(threads)
    unified_data["threads"] = threads
    
    # SAVE IMMEDIATELY after pre-processing (to the same file)
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(unified_data, f, indent=2)
    print(f"[+] Pre-processed data saved to {filename}")
    
    # 2. LLM Consolidation
    assets = get_unique_assets(threads)
    mapping = generate_mapping(assets)
    
    if mapping:
        print(f"[*] Identified {len(mapping)} merge rules.")
        threads = apply_mapping(threads, mapping)
        unified_data["threads"] = threads
        
        # Save to consolidated file (Overwriting the source file)
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(unified_data, f, indent=2)
        print(f"[+] Consolidated data saved to {filename}")
        
    else:
        print("[!] No mapping generated (or error).")

    # 3. Trigger Dashboard Aggregation (embeds into same file)
    aggregate_dashboard_data()

def generate_grand_metanarrative(threads):
    """
    Synthesizes a grand metanarrative from all threads - the overall market vibe.
    Returns a dict with 'narrative' and 'generated_at' date.
    Uses Pro model for higher quality synthesis, with Flash as fallback.
    """
    if not threads:
        return {'narrative': None, 'generated_at': None}
    
    # Gather gestalt summaries and radar data
    summaries = []
    total_greed = 0
    total_fear = 0
    total_schizo = 0
    
    for thread in threads[:30]:  # Cap at 30 threads to fit context
        if 'gestalt_summary' in thread:
            summaries.append(thread['gestalt_summary'])
        radar = thread.get('radar', {})
        total_greed += radar.get('GREED', 0)
        total_fear += radar.get('FEAR', 0)
        total_schizo += radar.get('SCHIZO', 0)
    
    if not summaries:
        return {'narrative': None, 'generated_at': None}
    
    n = len(summaries)
    avg_greed = total_greed / n
    avg_fear = total_fear / n
    avg_schizo = total_schizo / n
    
    prompt = f"""
    You are the oracle of 4chan /biz/, synthesizing the collective unconscious of degenerate traders.
    
    Below are {len(summaries)} gestalt summaries from recent threads:
    {json.dumps(summaries, indent=2)}
    
    Aggregate sentiment metrics:
    - Average GREED: {avg_greed:.0f}/100
    - Average FEAR: {avg_fear:.0f}/100  
    - Average SCHIZO: {avg_schizo:.0f}/100
    
    Task: Write a GRAND METANARRATIVE - a rich 4-6 sentence synthesis of the overall market mood.
    
    Guidelines:
    - Capture the zeitgeist: What is /biz/ FEELING right now?
    - Identify the dominant narratives, tribal conflicts, and emotional undercurrents
    - Reference specific themes: what assets are being shilled/fudded, what macro fears loom, what hopium is being huffed
    - Be poetic but substantive - like a gonzo journalist embedded in the trading trenches
    - Match the /biz/ energy: irreverent, sharp, occasionally unhinged
    - This is the VIBE CHECK for the entire board - make it count
    
    Return ONLY the metanarrative text, no quotes or formatting.
    """
    
    # Try Pro model first, fallback to Flash if it fails
    models_to_try = []
    if model_pro:
        models_to_try.append((model_pro, MODEL_PRO))
    if model:
        models_to_try.append((model, MODEL_FLASH))
    
    if not models_to_try:
        print("[!] No model available - skipping grand metanarrative generation.")
        return {'narrative': None, 'generated_at': None}
    
    for active_model, model_name in models_to_try:
        try:
            print(f"[*] Trying {model_name} for grand metanarrative...")
            response = active_model.generate_content(prompt)
            narrative = response.text.strip().strip('"')
            print(f"[+] Success with {model_name}")
            return {
                'narrative': narrative,
                'generated_at': datetime.now().strftime("%Y-%m-%d")
            }
        except Exception as e:
            print(f"[!] {model_name} failed: {e}")
            continue
    
    print("[!] All models failed for grand metanarrative.")
    return {'narrative': None, 'generated_at': None}


def generate_metathesis(asset_name, bullish_narratives, bearish_narratives):
    """
    Uses LLM to synthesize a metathesis from individual narratives.
    Returns dict with 'bullish' and 'bearish' metathesis strings.
    """
    if not model:
        # No model available - metathesis generation will be skipped
        return {'bullish': None, 'bearish': None}
    
    # Only generate if we have narratives to synthesize
    if not bullish_narratives and not bearish_narratives:
        return {'bullish': None, 'bearish': None}
    
    # Minimum threshold - don't synthesize if only 1-2 narratives
    MIN_NARRATIVES = 2
    
    result = {'bullish': None, 'bearish': None}
    
    # Generate Bullish Metathesis
    if len(bullish_narratives) >= MIN_NARRATIVES:
        bull_texts = [n['text'] for n in bullish_narratives]
        prompt = f"""
        You are synthesizing sentiment from 4chan /biz/ discussions about {asset_name}.
        
        Below are {len(bull_texts)} BULLISH narratives about this asset:
        {json.dumps(bull_texts, indent=2)}
        
        Task: Write a single, punchy 1-2 sentence METATHESIS that captures the core bullish case.
        - Be direct and confident, like a trader's conviction.
        - Capture the essence, not every detail.
        - Use active voice. No hedging language.
        - Match the /biz/ energy: sharp, irreverent, but insightful.
        
        Return ONLY the metathesis text, no quotes or formatting.
        """
        try:
            response = model.generate_content(prompt)
            result['bullish'] = response.text.strip().strip('"')
        except Exception as e:
            print(f"[!] Metathesis generation failed for {asset_name} (bullish): {e}")
    
    # Generate Bearish Metathesis
    if len(bearish_narratives) >= MIN_NARRATIVES:
        bear_texts = [n['text'] for n in bearish_narratives]
        prompt = f"""
        You are synthesizing sentiment from 4chan /biz/ discussions about {asset_name}.
        
        Below are {len(bear_texts)} BEARISH narratives about this asset:
        {json.dumps(bear_texts, indent=2)}
        
        Task: Write a single, punchy 1-2 sentence METATHESIS that captures the core bearish case.
        - Be direct and confident, like a trader's conviction.
        - Capture the essence, not every detail.
        - Use active voice. No hedging language.
        - Match the /biz/ energy: sharp, irreverent, but insightful.
        
        Return ONLY the metathesis text, no quotes or formatting.
        """
        try:
            response = model.generate_content(prompt)
            result['bearish'] = response.text.strip().strip('"')
        except Exception as e:
            print(f"[!] Metathesis generation failed for {asset_name} (bearish): {e}")
    
    return result


def aggregate_dashboard_data():
    """
    Aggregates raw gestalt data and embeds it into the unified timestamped JSON.
    Also generates dashboard_data.js for backwards compatibility with file:// access.
    """
    print("=== DASHBOARD AGGREGATOR ===")
    threads, unified_data, filename = load_data()
    if not threads:
        return

    # Load Canonicals
    try:
        if os.path.exists("canonical_assets.json"):
            with open("canonical_assets.json", 'r') as f:
                aliases = json.load(f)
        else:
            aliases = {}
    except:
        aliases = {}

    def normalize(n):
        upper = n.upper().strip()
        return aliases.get(upper, upper)

    # Track scan time range from thread timestamps
    scan_timestamps = []
    for thread in threads:
        if 'timestamp' in thread:
            scan_timestamps.append(thread['timestamp'])
    
    scan_range = {
        'earliest': min(scan_timestamps) if scan_timestamps else datetime.now().isoformat(),
        'latest': max(scan_timestamps) if scan_timestamps else datetime.now().isoformat()
    }
    print(f"[*] Scan range: {scan_range['earliest'][:10]} -> {scan_range['latest'][:10]}")

    # Aggregation State
    asset_map = {}
    global_greed = 0
    global_fear = 0
    
    for thread in threads:
        # Global Flux Metrics
        radar = thread.get('radar', {})
        global_greed += radar.get('GREED', 0)
        global_fear += radar.get('FEAR', 0)
        
        # Thread Score for Quote Selection (Chuckle + IQ)
        thread_score = radar.get('CHUCKLE_FACTOR', 0) + radar.get('IQ', 0)
        thread_quote = thread.get('top_quote', '')
        
        # Process Assets
        seen_in_thread = set()
        for asset in thread.get('assets', []):
            name = normalize(asset['name'])
            
            if name not in asset_map:
                asset_map[name] = {
                    'name': name,
                    'count': 0,
                    'sentimentScore': 0,
                    'narratives': [],
                    'threads': [],
                    'best_quote': '',
                    'best_quote_score': -1,
                    'chuckle_sum': 0,
                    'schizo_sum': 0,
                    'iq_sum': 0,
                    'greed_sum': 0,
                    'fear_sum': 0
                }
            
            # Update Counts
            asset_map[name]['count'] += 1
            if asset['sentiment'] == 'BULLISH':
                asset_map[name]['sentimentScore'] += 1
            elif asset['sentiment'] == 'BEARISH':
                asset_map[name]['sentimentScore'] -= 1
                
            # Add Narrative
            asset_map[name]['narratives'].append({
                'text': asset['narrative'],
                'sentiment': asset['sentiment'],
                'thread_id': thread['id'],
                'thread_sub': thread['subject']
            })
            
            # Track Threads
            if thread['id'] not in asset_map[name]['threads']:
                asset_map[name]['threads'].append(thread['id'])
                
            # Update Best Quote (Per Asset)
            if thread_quote and thread_score > asset_map[name]['best_quote_score']:
                asset_map[name]['best_quote'] = thread_quote
                asset_map[name]['best_quote_score'] = thread_score
                
            # Track Stats (for average) - Count once per thread per asset
            if thread['id'] not in seen_in_thread:
                asset_map[name]['chuckle_sum'] += radar.get('CHUCKLE_FACTOR', 0)
                asset_map[name]['schizo_sum'] += radar.get('SCHIZO', 0)
                asset_map[name]['iq_sum'] += radar.get('IQ', 0)
                asset_map[name]['greed_sum'] += radar.get('GREED', 0)
                asset_map[name]['fear_sum'] += radar.get('FEAR', 0)
                seen_in_thread.add(thread['id'])

    # Finalize Asset Data
    processed_assets = []
    assets_needing_metathesis = []
    
    for name, asset_data in asset_map.items():
        # Calculate derived metrics
        bullish_narratives = [n for n in asset_data['narratives'] if n['sentiment'] == 'BULLISH']
        bearish_narratives = [n for n in asset_data['narratives'] if n['sentiment'] == 'BEARISH']
        bullish = len(bullish_narratives)
        bearish = len(bearish_narratives)
        net_score = bullish - bearish
        
        # Controversy
        split = min(bullish, bearish) / ((bullish + bearish) / 2 or 1)
        controversy = round(split * 100)
        
        # Avg Stats
        unique_threads = len(asset_data['threads'])
        avg_chuckle = round(asset_data['chuckle_sum'] / unique_threads) if unique_threads > 0 else 0
        avg_schizo = round(asset_data['schizo_sum'] / unique_threads) if unique_threads > 0 else 0
        avg_iq = round(asset_data['iq_sum'] / unique_threads) if unique_threads > 0 else 0
        avg_greed = round(asset_data['greed_sum'] / unique_threads) if unique_threads > 0 else 0
        avg_fear = round(asset_data['fear_sum'] / unique_threads) if unique_threads > 0 else 0

        asset_entry = {
            'name': name,
            'count': asset_data['count'],
            'sentimentScore': asset_data['sentimentScore'],
            'bullishCount': bullish,
            'bearishCount': bearish,
            'netScore': net_score,
            'controversyScore': controversy,
            'avgChuckle': avg_chuckle,
            'avgSchizo': avg_schizo,
            'avgIQ': avg_iq,
            'avgGreed': avg_greed,
            'avgFear': avg_fear,
            'bestQuote': asset_data['best_quote'],
            'narratives': asset_data['narratives'],
            'threads': asset_data['threads'],
            'bullishMetathesis': None,
            'bullishMetathesisDate': None,
            'bearishMetathesis': None,
            'bearishMetathesisDate': None
        }
        
        processed_assets.append(asset_entry)
        
        # Queue for metathesis generation if enough narratives
        if bullish >= 2 or bearish >= 2:
            assets_needing_metathesis.append((asset_entry, bullish_narratives, bearish_narratives))
    
    # Generate Grand Metanarrative (overall market vibe)
    print("[*] Generating grand metanarrative...")
    grand_meta = generate_grand_metanarrative(threads)
    if grand_meta['narrative']:
        print(f"[+] Grand metanarrative generated.")
    
    # Generate Metatheses (batched after main loop to show progress)
    metathesis_date = datetime.now().strftime("%Y-%m-%d")
    if assets_needing_metathesis and model:
        print(f"[*] Generating metatheses for {len(assets_needing_metathesis)} assets...")
        for i, (asset_entry, bull_narr, bear_narr) in enumerate(assets_needing_metathesis):
            print(f"    > [{i+1}/{len(assets_needing_metathesis)}] {asset_entry['name']}...")
            metathesis = generate_metathesis(asset_entry['name'], bull_narr, bear_narr)
            asset_entry['bullishMetathesis'] = metathesis['bullish']
            asset_entry['bullishMetathesisDate'] = metathesis_date if metathesis['bullish'] else None
            asset_entry['bearishMetathesis'] = metathesis['bearish']
            asset_entry['bearishMetathesisDate'] = metathesis_date if metathesis['bearish'] else None

    # Finalize Global Flux
    total_threads = len(threads) or 1
    avg_greed = global_greed / total_threads
    avg_fear = global_fear / total_threads
    total_intensity = avg_greed + avg_fear or 1
    flux_score = (avg_greed / total_intensity) * 100
    
    dashboard_data = {
        "metadata": {
            "generated_at": datetime.now().isoformat(),
            "scan_range": scan_range,
            "total_threads": total_threads,
            "flux_score": round(flux_score),
            "grand_metanarrative": grand_meta['narrative'],
            "grand_metanarrative_date": grand_meta['generated_at']
        },
        "assets": processed_assets
    }
    
    # EMBED dashboard data into the unified timestamped JSON (PRIMARY)
    unified_data["dashboard"] = dashboard_data
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(unified_data, f, indent=2)
    print(f"[+] Dashboard data embedded into {filename}")
        
    # Also save as JS for local file:// access (extracts dashboard from latest)
    js_content = f"window.AURA_DASHBOARD_DATA = {json.dumps(dashboard_data, indent=2)};"
    with open("dashboard_data.js", 'w', encoding='utf-8') as f:
        f.write(js_content)
        
    print(f"[+] Dashboard JS updated: dashboard_data.js ({len(processed_assets)} assets)")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--aggregate":
        aggregate_dashboard_data()
    else:
        consolidate()
