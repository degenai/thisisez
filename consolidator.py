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
if API_KEY:
    genai.configure(api_key=API_KEY)
    model = genai.GenerativeModel('gemini-2.5-flash')
else:
    print("[!] ERROR: NO API KEY FOUND.")
    model = None

def load_data():
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
        return None, None
        
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            return json.load(f), filename
    except Exception as e:
        print(f"[!] Error loading data: {e}")
        return None, None

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
    data, filename = load_data()
    if not data:
        return
    
    # 1. Deterministic Pre-processing
    data = pre_process_data(data)
    
    # SAVE IMMEDIATELY after pre-processing (to the same file)
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)
    print(f"[+] Pre-processed data saved to {filename}")
    
    # 2. LLM Consolidation
    assets = get_unique_assets(data)
    mapping = generate_mapping(assets)
    
    if mapping:
        print(f"[*] Identified {len(mapping)} merge rules.")
        new_data = apply_mapping(data, mapping)
        
        # Save to consolidated file (Overwriting the source file)
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(new_data, f, indent=2)
        print(f"[+] Consolidated data saved to {filename}")
        
    else:
        print("[!] No mapping generated (or error).")

    # 3. Trigger Dashboard Aggregation
    aggregate_dashboard_data()

def aggregate_dashboard_data():
    """
    Aggregates raw gestalt data into a clean JSON for the frontend (combinator.html).
    Moves 'data hygenics' from JS to Python.
    """
    print("=== DASHBOARD AGGREGATOR ===")
    data, filename = load_data()
    if not data:
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

    # Aggregation State
    asset_map = {}
    global_greed = 0
    global_fear = 0
    
    for thread in data:
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
            # If this thread has a better quote than what we have stored for this asset, take it.
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
    for name, data in asset_map.items():
        # Calculate derived metrics
        bullish = len([n for n in data['narratives'] if n['sentiment'] == 'BULLISH'])
        bearish = len([n for n in data['narratives'] if n['sentiment'] == 'BEARISH'])
        net_score = bullish - bearish
        
        # Controversy
        total_mentions = bullish + bearish
        split = min(bullish, bearish) / ((bullish + bearish) / 2 or 1)
        controversy = round(split * 100)
        
        # Avg Stats
        unique_threads = len(data['threads'])
        avg_chuckle = round(data['chuckle_sum'] / unique_threads) if unique_threads > 0 else 0
        avg_schizo = round(data['schizo_sum'] / unique_threads) if unique_threads > 0 else 0
        avg_iq = round(data['iq_sum'] / unique_threads) if unique_threads > 0 else 0
        avg_greed = round(data['greed_sum'] / unique_threads) if unique_threads > 0 else 0
        avg_fear = round(data['fear_sum'] / unique_threads) if unique_threads > 0 else 0

        processed_assets.append({
            'name': name,
            'count': data['count'],
            'sentimentScore': data['sentimentScore'],
            'bullishCount': bullish,
            'bearishCount': bearish,
            'netScore': net_score,
            'controversyScore': controversy,
            'avgChuckle': avg_chuckle,
            'avgSchizo': avg_schizo,
            'avgIQ': avg_iq,
            'avgGreed': avg_greed,
            'avgFear': avg_fear,
            'bestQuote': data['best_quote'],
            'narratives': data['narratives'],
            'threads': data['threads']
        })

    # Finalize Global Flux
    total_threads = len(data) or 1
    avg_greed = global_greed / total_threads
    avg_fear = global_fear / total_threads
    total_intensity = avg_greed + avg_fear or 1
    flux_score = (avg_greed / total_intensity) * 100
    
    dashboard_data = {
        "metadata": {
            "generated_at": datetime.now().isoformat(),
            "total_threads": total_threads,
            "flux_score": round(flux_score)
        },
        "assets": processed_assets
    }
    
    # Save as JSON (for reference/API)
    with open("dashboard_data.json", 'w', encoding='utf-8') as f:
        json.dump(dashboard_data, f, indent=2)
        
    # Save as JS (for local file:// access)
    js_content = f"window.AURA_DASHBOARD_DATA = {json.dumps(dashboard_data, indent=2)};"
    with open("dashboard_data.js", 'w', encoding='utf-8') as f:
        f.write(js_content)
        
    print(f"[+] Dashboard data generated: dashboard_data.json & dashboard_data.js ({len(processed_assets)} assets)")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--aggregate":
        aggregate_dashboard_data()
    else:
        consolidate()
