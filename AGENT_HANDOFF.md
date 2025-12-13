# Agent Handoff: AURA FARMER Project

## Project Overview

**AURA FARMER** is a sentiment analysis dashboard that scrapes 4chan's /biz/ board, uses Gemini LLM to extract "gestalts" (psychological/market narratives), and displays aggregated sentiment data in a retro terminal-style web dashboard.

**Website URL:** Hosted on Cloudflare (check `CNAME` file for domain)  
**Entry Point:** `dashboard.html` (the main aura farmer interface)

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           LOCAL HARVESTING PIPELINE                          │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  local_gui.py ──▶ harvester.py ──▶ gestalt_export_*.json                    │
│       │                                    │                                 │
│       │                                    ▼                                 │
│       │                           consolidator.py                            │
│       │                                    │                                 │
│       │                                    ▼                                 │
│       │                    dashboard_data.json / .js                         │
│       │                                    │                                 │
│       ▼                                    ▼                                 │
│  [Tkinter GUI]                    [Web Dashboard]                            │
│  - Start/Stop harvest             dashboard.html                             │
│  - Auto-consolidate               - Leaderboard                              │
│  - Chiptune player                - Asset details                            │
│  - 3D visualizer                  - Flux meter                               │
│                                   - Grand metanarrative                      │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Key Files

### Python Backend

| File | Purpose |
|------|---------|
| `local_gui.py` | Tkinter GUI for running harvests locally. Has 3D sphere visualizer, chiptune player, interval scheduling. |
| `harvester.py` | Scrapes /biz/ catalog, fetches thread images, calls Gemini to extract gestalts. Outputs timestamped JSON exports. |
| `consolidator.py` | Cleans asset names, LLM-deduplicates synonyms, aggregates into dashboard format, generates metatheses. |
| `janitor.py` | Interactive CLI for managing canonical asset aliases. Scans exports, uses LLM to propose merges, human reviews. |
| `canonical_assets.json` | Alias mappings (e.g., "LINK" → "CHAINLINK"). Applied during consolidation. |

### Frontend

| File | Purpose |
|------|---------|
| `dashboard.html` | Main dashboard entry point. Terminal aesthetic with 3-column layout. |
| `js/app.js` | App initialization, data loading, component orchestration. |
| `js/leaderboard.js` | Left panel - ranked asset list with sentiment scores. |
| `js/details.js` | Center panel - asset details with bull/bear thesis columns, metatheses. |
| `js/flux.js` | Right panel - greed/fear gauge visualization. |
| `js/importer.js` | Handles JSON file uploads, localStorage persistence, client-side aggregation. |
| `css/dashboard.css` | Full terminal/keygen aesthetic styling. |

### Data Files

| File | Purpose |
|------|---------|
| `gestalt_export_*.json` | **Unified JSON** with both raw threads AND aggregated dashboard data. Latest 5 kept in root, older archived to `scanexports/`. |
| `latest_manifest.json` | Points to most recent gestalt export. |
| `dashboard_data.js` | Extracted dashboard data as JS global (for file:// access). Generated from latest timestamped JSON. |

---

## Data Flow

### Unified JSON Format (Timestamped JSON Primacy)

Each timestamped export is a **self-contained unified JSON** with both raw threads and aggregated dashboard data:

```json
{
  "threads": [...],      // Raw thread data from harvester
  "dashboard": {         // Aggregated view (populated by consolidator)
    "metadata": {...},
    "assets": [...]
  }
}
```

This enables archivable JSONs that can be used for historical analysis and date range queries.

### Harvesting Pipeline

1. **`local_gui.py`** starts harvest cycle
2. **`harvester.py`** scans /biz/ catalog for active threads (>5 replies)
3. For each thread:
   - Fetch full thread JSON from 4chan API
   - Fetch OP image if present
   - Send to Gemini with analysis prompt
   - Extract: gestalt summary, radar scores (GREED/FEAR/SCHIZO/IQ/SHILL/CHUCKLE), assets mentioned, top quote
4. Export to `gestalt_export_YYYYMMDD_HHMMSS.json` (unified format)
5. Trigger consolidation (if not handled by GUI)

### Consolidation Pipeline

1. **Pre-process**: Strip parenthetical tickers, apply canonical aliases
2. **LLM Mapping**: Gemini identifies synonyms (e.g., "BTC" → "Bitcoin")
3. **Aggregation**: 
   - Group narratives by asset
   - Calculate sentiment scores, controversy, averages
   - Select best quotes per asset
4. **Metathesis Generation**:
   - Grand metanarrative (overall market vibe) - uses `gemini-3-pro-preview`
   - Per-asset bull/bear metatheses (if ≥2 narratives) - uses `gemini-2.5-flash`
5. **Embed**: Dashboard data is embedded into the same timestamped JSON
6. **Export**: `dashboard_data.js` generated for backwards compatibility

---

## Recent Session Work (December 2024)

### Features Added

1. **Metathesis Generation** (`consolidator.py`)
   - Per-asset synthesis of bullish/bearish narratives
   - Shows at top of thesis columns in dashboard
   - Only generates if ≥2 narratives exist
   - Fields: `bullishMetathesis`, `bearishMetathesis`, `*MetathesisDate`

2. **Grand Metanarrative** (`consolidator.py`)
   - Overall market vibe synthesis from all threads
   - Displays in center column when no asset selected
   - Fields in metadata: `grand_metanarrative`, `grand_metanarrative_date`

3. **Time Range Tracking**
   - `scan_range.earliest` / `scan_range.latest` in metadata
   - Header displays: `SYNC: Nov 28 → Dec 2`
   - Both consolidator.py and importer.js track this

4. **UI Updates** (`js/details.js`, `css/dashboard.css`)
   - Metathesis boxes with colored glows (green bullish, red bearish)
   - Grand metanarrative container with cyan glow
   - Date indicators on all metatheses

### Bug Fixes

1. **`harvester.py` line 91** - `distill_thread()` returned single value instead of tuple when no model available. Fixed to return `(mock_distill(thread), "NO_MODEL")`.

2. **`consolidator.py` variable shadowing** - Loop variable `for name, data in asset_map.items()` shadowed outer `data` variable, breaking `generate_grand_metanarrative(data)`. Renamed to `asset_data`.

3. **Unicode arrow in console** - `→` character caused Windows cp1252 encoding error. Changed to `->`.

4. **Double consolidation** - Both `harvester.main()` and GUI's auto-consolidate were running consolidation. Added `skip_consolidation` flag to prevent duplicate runs.

5. **`.env` BOM issue** - Windows Notepad added UTF-8 BOM breaking dotenv parsing. Recreated file without BOM.

---

## Environment Setup

### Required Environment Variables

```bash
# .env file in project root
GEMINI_API_KEY=<your-gemini-api-key>
```

### Dependencies

```bash
pip install -r requirements.txt
```

Key packages:
- `google-generativeai` - Gemini API
- `python-dotenv` - Environment loading
- `requests` - HTTP client
- `Pillow` - Image processing
- `pygame` - Audio playback (GUI chiptunes)

**Python Version:** 3.9+ (warnings about 3.9 EOL but functional)

---

## Running the Project

### Local GUI Method (Recommended)

```bash
python local_gui.py
```

- Click `[START HARVEST]` to begin
- Toggle `AUTO-CONSOLIDATE` for automatic dashboard updates
- Set `MAX THREADS` (0 = all active threads)
- Set `INTERVAL (HRS)` for recurring harvests
- Chiptunes in `chiptunes/` folder play during harvest

### Direct Harvest (CLI)

```bash
python harvester.py  # Runs full harvest + consolidation
```

### Manual Consolidation

```bash
python consolidator.py              # Full consolidation
python consolidator.py --aggregate  # Just aggregation (skip LLM dedup)
```

### Asset Alias Management (Janitor)

```bash
python janitor.py
```

The **Janitor** is an interactive tool for curating `canonical_assets.json`:

1. Scans recent gestalt exports for unique asset names
2. Uses LLM to propose alias mappings (e.g., "BTC" → "Bitcoin")
3. Human reviews each proposal: `y` (accept) / `n` (skip) / `x` (exit)
4. Approved mappings saved to `canonical_assets.json`

**When to run:** After several harvests when you notice redundant assets (e.g., "ETH" and "Ethereum" appearing separately in the leaderboard).

**How aliases work:** During consolidation, `clean_name()` applies these mappings BEFORE aggregation, so "BTC", "Bitcoin", and "$BTC" all become "BITCOIN".

### View Dashboard

- Open `dashboard.html` in browser (file:// works due to .js data file)
- Or serve via local server for .json fetching
- Use `[LOAD JSON]` button to import gestalt exports directly

---

## Planned Feature: D1 Cloud Sync

A plan exists at `.cursor/plans/d1_cloud_sync_system_*.plan.md` for:

- Cloudflare Worker API to store scans in D1 database
- Auto-push after each harvest
- Timeline slider UI with selectable range bounds
- Tick indicators showing available data points
- Historical scan browsing and comparison

**Status:** Not yet implemented.

---

## Test Suite

```bash
python -m pytest test_suite.py -v
```

Tests cover:
- Harvester catalog fetching (success/failure)
- Thread distillation (with model, without model)
- Gestalt export and manifest creation
- Consolidator data loading and alias mapping
- Janitor asset extraction and alias identification
- Image + quote extraction with mocked Gemini

---

## Known Bugs / TODO

1. ~~**Grand metanarrative not shown on initial load**~~ - **FIXED** - Added 100ms timeout in `js/app.js` init to ensure Details.clear() runs after all data loading completes.

2. **Grand metanarrative could be longer** - Prompt updated in `consolidator.py` from 2-3 sentences to 4-6 sentences with richer guidelines. **Needs verification on next harvest run.**

3. **Model selection** - ✅ **FIXED** (Dec 2024) - Now using `gemini-2.5-flash` for bulk operations (harvester, consolidator dedup, per-asset metatheses) and `gemini-3-pro-preview` for grand metanarrative generation. Janitor updated from deprecated `gemini-2.0-flash-exp` to `gemini-2.5-flash`. Model names are now defined as constants (`MODEL_FLASH`, `MODEL_PRO`) for easy updates.

---

## Notes for Next Agent

1. **Metathesis generation is slow** - One LLM call per qualifying asset. Full 124-thread harvest with many qualifying assets can take 10-20 minutes for consolidation.

2. **The dashboard works offline** - Uses `dashboard_data.js` for file:// access. The `.json` version is for future API/cloud use.

3. **Gestalt exports rotate** - Only 5 kept in root directory, older ones automatically moved to `scanexports/`.

4. **The GUI has chiptunes** - Music files in `chiptunes/` folder, played via pygame during harvest. Toggle with music button.

5. **`index.html` is NOT the aura farmer** - That's a separate landing page. The aura farmer dashboard is `dashboard.html`.

6. **Safety filters can block threads** - Gemini may refuse to analyze certain /biz/ content. These are logged and skipped gracefully.

7. **Variable naming in consolidator** - Be careful with `data` variable - it's used for the thread list. Don't shadow it in loops.

8. **Client-side aggregation exists** - `js/importer.js` has a full JavaScript implementation of the aggregation logic for direct JSON imports without Python.

---

## File Tree (Key Items)

```
jules/
├── dashboard.html          # Main aura farmer UI
├── index.html              # Landing page (separate)
├── local_gui.py            # Tkinter harvest controller
├── harvester.py            # Thread scraping + Gemini analysis
├── consolidator.py         # Data cleaning + aggregation + metathesis
├── janitor.py              # Canonical asset management
├── canonical_assets.json   # Alias mappings
├── latest_manifest.json    # Points to latest gestalt export
├── dashboard_data.json     # Aggregated data (JSON)
├── dashboard_data.js       # Aggregated data (JS global)
├── .env                    # API keys (not in repo)
├── requirements.txt        # Python dependencies
├── test_suite.py           # Unit tests
├── AGENT_HANDOFF.md        # This file
├── js/
│   ├── app.js              # Main app logic
│   ├── leaderboard.js      # Asset ranking panel
│   ├── details.js          # Asset detail view + metatheses
│   ├── flux.js             # Greed/fear gauge
│   └── importer.js         # JSON import + client aggregation
├── css/
│   └── dashboard.css       # Terminal aesthetic styles
├── chiptunes/              # Background music for GUI
├── scanexports/            # Archived gestalt exports
└── .cursor/plans/          # Implementation plans
```

