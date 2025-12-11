window.AURA = window.AURA || {};

window.AURA.App = {
    state: {
        data: null,
        selectedAsset: null
    },

    init: function () {
        console.log(":: AURA TERMINAL INITIALIZING ::");

        // Initialize Components
        window.AURA.Flux.init();
        window.AURA.Leaderboard.init((asset) => {
            this.state.selectedAsset = asset;
            window.AURA.Details.show(asset);
            // Update Flux for specific asset
            window.AURA.Flux.update(asset, null, true);
        });
        window.AURA.Details.init();
        window.AURA.Importer.init();

        // Load Data
        this.loadData();

        // Event Listeners
        const refreshBtn = document.getElementById('refresh-btn');
        if (refreshBtn) {
            refreshBtn.addEventListener('click', () => {
                location.reload();
            });
        }
    },

    loadData: function () {
        // Check for global data object injected by dashboard_data.js
        if (window.AURA_DASHBOARD_DATA) {
            console.log("[DATA] Found window.AURA_DASHBOARD_DATA");
            this.processData(window.AURA_DASHBOARD_DATA);
        } else {
            console.warn("[DATA] Data not found. Retrying in 500ms...");
            setTimeout(() => this.loadData(), 500);
        }
    },

    processData: function (rawData) {
        this.state.data = rawData;

        // Calculate total threads dynamically
        const uniqueThreads = new Set();
        if (rawData.assets && Array.isArray(rawData.assets)) {
            rawData.assets.forEach(a => {
                if (a.threads) {
                    a.threads.forEach(tid => uniqueThreads.add(tid));
                }
            });
        }
        const totalThreads = uniqueThreads.size;

        // Update Header Stats
        const totalThreadsEl = document.getElementById('total-threads');
        const lastUpdatedEl = document.getElementById('last-updated');

        if (totalThreadsEl) totalThreadsEl.textContent = `THREADS: ${totalThreads}`;
        if (lastUpdatedEl) {
            // Display scan range if available, otherwise single timestamp
            if (rawData.metadata.scan_range) {
                const earliest = new Date(rawData.metadata.scan_range.earliest);
                const latest = new Date(rawData.metadata.scan_range.latest);
                
                // Format as short date (Dec 1)
                const formatShort = (d) => d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
                
                // Check if same day
                const sameDay = earliest.toDateString() === latest.toDateString();
                
                if (sameDay) {
                    lastUpdatedEl.textContent = `SYNC: ${formatShort(latest)}`;
                } else {
                    lastUpdatedEl.textContent = `SYNC: ${formatShort(earliest)} → ${formatShort(latest)}`;
                }
            } else {
                const date = new Date(rawData.metadata.generated_at);
                lastUpdatedEl.textContent = `SYNC: ${date.toLocaleTimeString()}`;
            }
        }

        // Update Components
        window.AURA.Flux.update(rawData.metadata, rawData.assets);
        window.AURA.Leaderboard.render(rawData.assets);
    },

    clearSelection: function () {
        this.state.selectedAsset = null;
        // Reset Details View
        window.AURA.Details.clear();
        // Reset Flux to Global
        if (this.state.data) {
            window.AURA.Flux.update(this.state.data.metadata, this.state.data.assets, false);
        }
        // Deselect in Leaderboard
        window.AURA.Leaderboard.deselectAll();
    }
};

// Auto-start
document.addEventListener('DOMContentLoaded', () => {
    window.AURA.App.init();
});
