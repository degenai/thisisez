# AURA FARMER® GESTALT SCRAPER™

> "The Harvester extracts the value (Labor). The Gemini refines it (Imperial Processing). The Viewer displays it (The Spectacle)."

## Overview
Aura Farmer is a local-first intelligence tool that scrapes 4chan's /biz/ board, distills thread narratives using Google Gemini, and visualizes the "Gestalt" (Metanarrative) on a cyberpunk dashboard.

## ⚠️ CRITICAL: API Configuration
To use the Harvester, you **MUST** provide your own Google Gemini API Key.
This key is stored locally in a `.env` file and is **NEVER** committed to the repository.

### Setup Instructions
1.  Get your key from [Google AI Studio](https://aistudio.google.com/app/apikey).
2.  Locate the file named `.env.example`.
3.  Rename it to `.env`.
4.  Open it and paste your key:
    ```env
    GEMINI_API_KEY=AIzaSy...
    ```
5.  **DO NOT SHARE THIS FILE.** It is ignored by git for your safety.

## Usage
1.  **Run the Harvester:**
    - Double-click `run_harvester.bat` (Windows).
    - Or run `python harvester.py` in your terminal.
2.  **View Intelligence:**
    - Open `aura_farmer.html`.
    - Click `[↑] UPLINK INTELLIGENCE` and select the generated `gestalt_export.json`.

## Architecture
- **The Harvester (`harvester.py`)**: The worker. Scrapes raw data and interfaces with the AI.
- **The Viewer (`aura_farmer.html`)**: The interface. A static HTML file that reads local JSON data.
- **The Brain (Gemini)**: The imperial processor. Turns chaos into "Intelligence".

> "We are using the tools of the oppressor to analyze the screams of the oppressed speculators!" - Parenti (Simulated)
