import os
import json
import glob
import google.generativeai as genai
from dotenv import load_dotenv
import time
import sys

# Compatibility Patch for Python < 3.10
if sys.version_info < (3, 10):
    try:
        import importlib_metadata
        import importlib.metadata
        if not hasattr(importlib.metadata, 'packages_distributions'):
            importlib.metadata.packages_distributions = importlib_metadata.packages_distributions
    except ImportError:
        pass # importlib_metadata not installed

# Load Environment
load_dotenv()
API_KEY = os.getenv("GEMINI_API_KEY")

if not API_KEY:
    print("[!] ERROR: GEMINI_API_KEY not found in .env")
    exit(1)

genai.configure(api_key=API_KEY)

CANONICAL_FILE = "canonical_assets.json"

def load_canonical():
    if os.path.exists(CANONICAL_FILE):
        with open(CANONICAL_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_canonical(data):
    with open(CANONICAL_FILE, 'w') as f:
        json.dump(data, f, indent=4)
    print(f"[*] Updated {CANONICAL_FILE}")

def get_recent_exports(n=5):
    files = glob.glob("gestalt_export_*.json")
    files.sort(key=os.path.getmtime, reverse=True)
    return files[:n]

def extract_unique_assets(files):
    assets = set()
    for file in files:
        try:
            with open(file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                for item in data:
                    for asset in item.get('assets', []):
                        assets.add(asset['name'].upper().strip())
        except Exception as e:
            print(f"[!] Error reading {file}: {e}")
    return list(assets)

def identify_aliases(new_assets, canonical_map):
    # Filter out assets that are already canonical or aliased
    unknown_assets = [a for a in new_assets if a not in canonical_map and a not in canonical_map.values()]
    
    if not unknown_assets:
        print("[*] No new unknown assets found.")
        return []

    print(f"[*] Analyzing {len(unknown_assets)} unknown assets against known canonicals...")
    
    # Prepare prompt
    known_canonicals = list(set(canonical_map.values()))
    prompt = f"""
    You are a Data Janitor for a financial sentiment analysis tool (4chan /biz/).
    Your job is to map NEW, messy asset names to a CLEAN, canonical list.
    
    KNOWN CANONICAL ASSETS:
    {json.dumps(known_canonicals)}
    
    NEW UNKNOWN ASSETS:
    {json.dumps(unknown_assets)}
    
    IMPORTANT CONTEXT:
    - "Assets" include: Stocks, Cryptos, People (e.g. "Powell"), Concepts (e.g. "Inflation"), Commodities, and Memes.
    
    Task:
    1. Identify if any of the NEW assets are actually aliases for the KNOWN assets.
    2. Identify if any of the NEW assets are clearly the same thing as each other.
    
    NEGATIVE CONSTRAINTS:
    - Do NOT merge distinct products (e.g. "iPhone" != "Apple").
    - Do NOT merge distinct coins (e.g. "DOGE" != "SHIB").
    
    Output a JSON list of proposed mappings. ONLY output mappings where you are confident.
    Format: [{{"alias": "MESSY_NAME", "canonical": "CLEAN_NAME"}}]
    """
    
    try:
        model = genai.GenerativeModel('gemini-2.0-flash-exp')
        response = model.generate_content(prompt)
        text = response.text.strip()
        # Clean markdown
        if text.startswith("```json"):
            text = text[7:-3]
        return json.loads(text)
    except Exception as e:
        print(f"[!] LLM Error: {e}")
        return []

def main():
    print("::: AURA JANITOR v1.0 :::")
    
    # 1. Load State
    canonical = load_canonical()
    print(f"[*] Loaded {len(canonical)} canonical rules.")
    
    # 2. Scan Files
    try:
        n = int(input("[?] How many recent export files to scan? (Default 5): ") or 5)
    except:
        n = 5
        
    files = get_recent_exports(n)
    print(f"[*] Scanning {len(files)} files...")
    
    # 3. Extract
    unique_assets = extract_unique_assets(files)
    print(f"[*] Found {len(unique_assets)} unique asset names.")
    
    # 4. Analyze
    proposals = identify_aliases(unique_assets, canonical)
    
    if not proposals:
        print("[*] No new aliases proposed.")
        return

    # 5. Interactive Review
    print(f"\n[!] Proposed {len(proposals)} new aliases:")
    count = 0
    for p in proposals:
        alias = p['alias'].upper()
        canon = p['canonical'].upper()
        
        if alias in canonical:
            continue
            
        print(f"\n[?] Map '{alias}' -> '{canon}'? (y/n/x to exit)")
        choice = input("> ").lower().strip()
        
        if choice == 'y':
            canonical[alias] = canon
            count += 1
        elif choice == 'x':
            break
            
    # 6. Save
    if count > 0:
        save_canonical(canonical)
        print(f"[*] Saved {count} new rules.")
    else:
        print("[*] No changes made.")

if __name__ == "__main__":
    main()
