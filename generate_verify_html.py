import json
import os
from datetime import datetime, timedelta

def main():
    # Read the HTML template
    with open('combinator.html', 'r', encoding='utf-8') as f:
        html_content = f.read()

    # Generate Mock Data with Temporal Spread
    base_time = datetime.now()
    data = []

    # Helper to add items
    def add_items(day_offset, count, sentiment_bias):
        for i in range(count):
            ts = base_time - timedelta(days=day_offset)
            data.append({
                "id": f"thread_{day_offset}_{i}",
                "timestamp": ts.isoformat(),
                "subject": f"Day {day_offset+1} Thread {i}", # Adjust subject to match 1-indexed day
                "url": "https://boards.4channel.org/biz/",
                "replies": 10 + i,
                "gestalt_summary": "Mock data for verification.",
                "radar": {"GREED": 50 + (10 if sentiment_bias == 'bull' else -10), "FEAR": 50, "IQ": 50, "SCHIZO": 50, "SHILL": 50},
                "keywords": ["MOCK"],
                "assets": [
                    {"name": "BITCOIN", "narrative": "Mock narrative", "sentiment": "BULLISH" if sentiment_bias == 'bull' else "BEARISH"}
                ]
            })

    # Create Timeline:
    # Day 1: 5 items (day_offset=0)
    # Day 2: 0 items (Gap) (day_offset=1)
    # Day 3: 10 items (day_offset=2)
    # Day 4: 2 items (day_offset=3)
    add_items(0, 5, 'bull')   # Day 1
    # Day 2 is GAP (no items for day_offset=1)
    add_items(2, 10, 'bull')  # Day 3
    add_items(3, 2, 'bear')   # Day 4

    # Let's just replace the window.addEventListener block to load our mock data directly.
    # The original has: window.addEventListener('DOMContentLoaded', () => { loadAndRender(); });
    # We'll replace this entire block with our custom loader.

    # Find the original DOMContentLoaded listener
    # This assumes a specific structure for the original listener.
    # A more robust solution might involve parsing the HTML/JS or using a placeholder.
    original_listener_start = "window.addEventListener('DOMContentLoaded', () => {"
    original_listener_end = "});"
    
    # Find the start and end indices of the original listener
    start_idx = html_content.find(original_listener_start)
    
    if start_idx == -1:
        print("Error: Original DOMContentLoaded listener not found. Cannot inject mock data.")
        return

    # Find the matching closing brace for the DOMContentLoaded listener
    # This is a simple approach and might fail for complex JS.
    # We'll look for the first '});' after the start of the listener.
    end_idx = html_content.find(original_listener_end, start_idx + len(original_listener_start))

    if end_idx == -1:
        print("Error: Closing '});' for DOMContentLoaded listener not found. Cannot inject mock data.")
        return
    
    # The new loader script
    new_loader = f"""
window.addEventListener('DOMContentLoaded', () => {{
    const data = {json.dumps(data)};
    console.log("VERIFICATION MODE: MOCK DATA LOADED");
    processCombinator(data);
    renderTemporalGraph(data);
    alert("VERIFICATION MODE: MOCK DATA LOADED");
}});
"""
    
    # Replace the original listener block with the new one
    new_html = html_content[:start_idx] + new_loader + html_content[end_idx + len(original_listener_end):]

    # Write to verification file
    with open('combinator_verify.html', 'w', encoding='utf-8') as f:
        f.write(new_html)

    print("Created combinator_verify.html with temporal mock data")

if __name__ == "__main__":
    main()
