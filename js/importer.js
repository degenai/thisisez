window.AURA = window.AURA || {};

window.AURA.Importer = {
    init: function () {
        // 1. Create hidden file input
        const input = document.createElement('input');
        input.type = 'file';
        input.accept = '.json';
        input.multiple = true; // Allow multiple files
        input.style.display = 'none';
        input.id = 'json-upload-input';
        document.body.appendChild(input);

        input.addEventListener('change', (e) => this.handleFileSelect(e));

        // 2. Add Controls to Header
        const controls = document.querySelector('.header-controls');
        if (controls) {
            // Clear Button
            const clearBtn = document.createElement('button');
            clearBtn.className = 'btn-text';
            clearBtn.textContent = '[PURGE DATA]';
            clearBtn.style.color = 'var(--c-fear)';
            clearBtn.style.marginRight = '10px';
            clearBtn.onclick = () => this.clearData();

            // Load Button
            const loadBtn = document.createElement('button');
            loadBtn.className = 'btn-text';
            loadBtn.textContent = '[LOAD JSON]';
            loadBtn.onclick = () => input.click();

            // Insert at beginning
            controls.insertBefore(loadBtn, controls.firstChild);
            controls.insertBefore(clearBtn, controls.firstChild);
        }

        // 3. Load from Memory on Init
        this.loadFromMemory();
    },

    handleFileSelect: function (event) {
        const files = Array.from(event.target.files);
        if (files.length === 0) return;

        console.log(`[IMPORTER] Reading ${files.length} files...`);

        const promises = files.map(file => {
            return new Promise((resolve, reject) => {
                const reader = new FileReader();
                reader.onload = (e) => {
                    try {
                        const json = JSON.parse(e.target.result);
                        resolve(json);
                    } catch (err) {
                        console.error(`Error parsing ${file.name}`, err);
                        resolve(null); // Skip bad files
                    }
                };
                reader.readAsText(file);
            });
        });

        Promise.all(promises).then(results => {
            const validData = results.filter(d => d !== null);
            this.processImport(validData);
        });
    },

    processImport: function (dataList) {
        let allThreads = [];
        let isPreAggregated = false;

        dataList.forEach(data => {
            // Case 1: Already Aggregated
            if (data.metadata && data.assets) {
                console.log("[IMPORTER] Loaded Pre-Aggregated Data");
                // For now, we just take the first aggregated file if multiple
                // Merging aggregated data is complex, so we prioritize raw data merging
                if (!isPreAggregated) {
                    window.AURA.App.processData(data);
                    isPreAggregated = true;
                }
                return;
            }

            // Case 2: Raw Gestalt Export (List or Single Object)
            if (Array.isArray(data)) {
                allThreads = allThreads.concat(data);
            } else if (data.id && data.subject) {
                allThreads.push(data);
            }
        });

        if (allThreads.length > 0) {
            console.log(`[IMPORTER] Aggregating ${allThreads.length} raw threads...`);

            // Merge with existing memory if desired? 
            // For now, let's append to existing memory to mimic "Uplink" behavior
            const existing = this.getStoredThreads();
            const merged = this.mergeThreads(existing, allThreads);

            this.saveToMemory(merged);

            const aggregated = this.aggregateRawData(merged);
            window.AURA.App.processData(aggregated);
        }
    },

    mergeThreads: function (existing, newThreads) {
        const map = new Map();

        // Load existing
        existing.forEach(t => map.set(t.id, t));

        // Merge new (overwrite if newer/longer?)
        newThreads.forEach(t => {
            if (map.has(t.id)) {
                // Simple dedup: keep the one with more replies or just overwrite
                map.set(t.id, t);
            } else {
                map.set(t.id, t);
            }
        });

        return Array.from(map.values());
    },

    saveToMemory: function (threads) {
        try {
            localStorage.setItem('aura_gestalt_data', JSON.stringify(threads));
            console.log(`[IMPORTER] Saved ${threads.length} threads to local storage.`);
        } catch (e) {
            console.error("Local Storage Full/Error", e);
        }
    },

    getStoredThreads: function () {
        try {
            const stored = localStorage.getItem('aura_gestalt_data');
            return stored ? JSON.parse(stored) : [];
        } catch (e) {
            return [];
        }
    },

    loadFromMemory: function () {
        const threads = this.getStoredThreads();
        if (threads.length > 0) {
            console.log(`[IMPORTER] Loaded ${threads.length} threads from memory.`);
            const aggregated = this.aggregateRawData(threads);
            window.AURA.App.processData(aggregated);
        } else {
            console.log("[IMPORTER] No local data found. Waiting for default data or upload.");
        }
    },

    clearData: function () {
        if (confirm("PURGE ALL LOCAL DATA?")) {
            localStorage.removeItem('aura_gestalt_data');
            // Instead of reload, just clear the app state
            window.AURA.App.processData({
                metadata: {
                    generated_at: new Date().toISOString(),
                    total_threads: 0,
                    flux_score: 50
                },
                assets: []
            });
            // Also clear details view
            window.AURA.Details.clear();
        }
    },

    // Client-side version of consolidator.py logic
    aggregateRawData: function (threads) {
        let globalGreed = 0;
        let globalFear = 0;
        let globalSchizo = 0;
        let globalIQ = 0;
        let globalChuckle = 0;
        const assetMap = {};

        threads.forEach(thread => {
            const radar = thread.radar || {};
            globalGreed += (radar.GREED || 0);
            globalFear += (radar.FEAR || 0);
            globalSchizo += (radar.SCHIZO || 0);
            globalIQ += (radar.IQ || 0);
            globalChuckle += (radar.CHUCKLE_FACTOR || 0);

            const threadScore = (radar.CHUCKLE_FACTOR || 0) + (radar.IQ || 0);
            const threadQuote = thread.top_quote || "";

            const seenInThread = new Set(); // Track unique thread stats per asset

            (thread.assets || []).forEach(asset => {
                const name = asset.name.toUpperCase().trim().replace(/\s*\([^)]+\)$/, '');

                if (!assetMap[name]) {
                    assetMap[name] = {
                        name: name,
                        count: 0,
                        sentimentScore: 0,
                        narratives: [],
                        threads: [],
                        bestQuote: "",
                        bestQuoteScore: -1,
                        chuckleSum: 0,
                        schizoSum: 0,
                        iqSum: 0,
                        greedSum: 0,
                        fearSum: 0
                    };
                }

                const entry = assetMap[name];
                entry.count++;

                if (asset.sentiment === 'BULLISH') entry.sentimentScore++;
                if (asset.sentiment === 'BEARISH') entry.sentimentScore--;

                entry.narratives.push({
                    text: asset.narrative,
                    sentiment: asset.sentiment,
                    thread_sub: thread.subject || "No Subject"
                });

                if (!entry.threads.includes(thread.id)) {
                    entry.threads.push(thread.id);
                    // Add stats only once per thread per asset
                    entry.chuckleSum += (radar.CHUCKLE_FACTOR || 0);
                    entry.schizoSum += (radar.SCHIZO || 0);
                    entry.iqSum += (radar.IQ || 0);
                    entry.greedSum += (radar.GREED || 0);
                    entry.fearSum += (radar.FEAR || 0);
                }

                if (threadQuote && threadScore > entry.bestQuoteScore) {
                    entry.bestQuote = threadQuote;
                    entry.bestQuoteScore = threadScore;
                }
            });
        });

        // Finalize Assets
        const processedAssets = Object.values(assetMap).map(data => {
            const bullish = data.narratives.filter(n => n.sentiment === 'BULLISH').length;
            const bearish = data.narratives.filter(n => n.sentiment === 'BEARISH').length;
            const total = bullish + bearish || 1;

            // Controversy: Ratio of min/avg
            const split = Math.min(bullish, bearish) / (total / 2);
            const controversy = Math.round(split * 100) || 0;

            const uniqueThreads = data.threads.length || 1;
            const avgChuckle = Math.round(data.chuckleSum / uniqueThreads);
            const avgSchizo = Math.round(data.schizoSum / uniqueThreads);
            const avgIQ = Math.round(data.iqSum / uniqueThreads);
            const avgGreed = Math.round(data.greedSum / uniqueThreads);
            const avgFear = Math.round(data.fearSum / uniqueThreads);

            return {
                name: data.name,
                count: data.count,
                sentimentScore: data.sentimentScore,
                bullishCount: bullish,
                bearishCount: bearish,
                netScore: bullish - bearish,
                controversyScore: controversy,
                avgChuckle: avgChuckle,
                avgSchizo: avgSchizo,
                avgIQ: avgIQ,
                avgGreed: avgGreed,
                avgFear: avgFear,
                bestQuote: data.bestQuote,
                narratives: data.narratives,
                threads: data.threads
            };
        });

        // Finalize Flux & Global Stats
        const totalThreads = threads.length || 1;
        const avgGreed = globalGreed / totalThreads;
        const avgFear = globalFear / totalThreads;
        const totalIntensity = avgGreed + avgFear || 1;
        const fluxScore = Math.round((avgGreed / totalIntensity) * 100);

        const globalAvgSchizo = Math.round(globalSchizo / totalThreads);
        const globalAvgIQ = Math.round(globalIQ / totalThreads);
        const globalAvgChuckle = Math.round(globalChuckle / totalThreads);

        // Track scan time range from thread timestamps
        const timestamps = threads
            .map(t => t.timestamp)
            .filter(t => t)
            .sort();
        
        const scanRange = timestamps.length > 0 ? {
            earliest: timestamps[0],
            latest: timestamps[timestamps.length - 1]
        } : {
            earliest: new Date().toISOString(),
            latest: new Date().toISOString()
        };

        return {
            metadata: {
                generated_at: new Date().toISOString(),
                scan_range: scanRange,
                total_threads: totalThreads,
                flux_score: fluxScore,
                avg_schizo: globalAvgSchizo,
                avg_iq: globalAvgIQ,
                avg_chuckle: globalAvgChuckle
            },
            assets: processedAssets
        };
    }
};
