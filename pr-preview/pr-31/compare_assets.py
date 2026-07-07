import json
import os

RAW_FILE = "gestalt_export_20251125_034305.json"
CONSOLIDATED_FILE = "gestalt_consolidated.json"

def analyze(filename):
    if not os.path.exists(filename):
        print(f"File not found: {filename}")
        return None, None
    
    with open(filename, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    unique_assets = set()
    total_mentions = 0
    asset_counts = {}

    for entry in data:
        for asset in entry.get('assets', []):
            name = asset['name']
            unique_assets.add(name)
            total_mentions += 1
            asset_counts[name] = asset_counts.get(name, 0) + 1
            
    return unique_assets, asset_counts

def compare():
    print(f"Comparing {RAW_FILE} vs {CONSOLIDATED_FILE}...")
    
    raw_assets, raw_counts = analyze(RAW_FILE)
    cons_assets, cons_counts = analyze(CONSOLIDATED_FILE)
    
    if not raw_assets or not cons_assets:
        return

    print(f"\n--- STATS ---")
    print(f"Raw Unique Assets: {len(raw_assets)}")
    print(f"Consolidated Unique Assets: {len(cons_assets)}")
    print(f"Reduction: {len(raw_assets) - len(cons_assets)} assets merged.")
    
    print(f"\n--- TOP MERGES (Estimated) ---")
    # Find assets that disappeared or increased significantly
    
    # Simple check: Which assets are in Raw but not in Consolidated?
    merged_away = raw_assets - cons_assets
    print(f"Assets Merged Away (Top 10): {list(merged_away)[:10]}")
    
    # Check for volume increases in consolidated
    print("\n--- VOLUME SHIFTS (Top 5 Gainers) ---")
    gains = []
    for name in cons_assets:
        r_count = raw_counts.get(name, 0)
        c_count = cons_counts.get(name, 0)
        if c_count > r_count:
            gains.append((name, r_count, c_count, c_count - r_count))
            
    gains.sort(key=lambda x: x[3], reverse=True)
    for name, r, c, diff in gains[:10]:
        print(f"{name}: {r} -> {c} (+{diff})")

    print(f"\n--- LOW VOLUME ANALYSIS (Count = 1) ---")
    singles = [name for name, count in cons_counts.items() if count == 1]
    print(f"Total Single-Occurrence Assets: {len(singles)}")
    print(f"Sample (First 50): {singles[:50]}")

if __name__ == "__main__":
    compare()
