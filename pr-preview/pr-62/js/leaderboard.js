window.AURA = window.AURA || {};

window.AURA.Leaderboard = {
    onSelectCallback: null,
    currentAssets: [],

    init: function (callback) {
        this.onSelectCallback = callback;

        const searchInput = document.getElementById('search-input');
        if (searchInput) {
            searchInput.addEventListener('input', (e) => {
                const term = e.target.value.toLowerCase();
                const filtered = this.currentAssets.filter(a => a.name.toLowerCase().includes(term));
                this.renderList(filtered);
            });
        }
    },

    render: function (assets) {
        this.currentAssets = assets;
        // Sort by Volume (count) default
        assets.sort((a, b) => b.count - a.count);
        this.renderList(assets);
    },

    renderList: function (assets) {
        const list = document.getElementById('leaderboard-list');
        if (!list) return;
        list.innerHTML = '';

        assets.forEach((asset, index) => {
            const row = document.createElement('div');
            row.className = 'lb-row';
            row.onclick = () => {
                // Active state
                document.querySelectorAll('.lb-row').forEach(r => r.classList.remove('active'));
                row.classList.add('active');

                if (this.onSelectCallback) this.onSelectCallback(asset);
            };

            // Trend Icon
            let trend = "→";
            let trendColor = "#666";
            if (asset.netScore > 0) { trend = "↗"; trendColor = "var(--c-greed)"; }
            if (asset.netScore < 0) { trend = "↘"; trendColor = "var(--c-fear)"; }
            if (asset.netScore > 5) trend = "↑";
            if (asset.netScore < -5) trend = "↓";

            row.innerHTML = `
                <div class="lb-rank">${index + 1}</div>
                <div class="lb-name">${asset.name}</div>
                <div class="lb-score" style="color: ${trendColor}">${asset.netScore > 0 ? '+' : ''}${asset.netScore}</div>
                <div class="lb-trend" style="color: ${trendColor}">${trend}</div>
            `;
            list.appendChild(row);
        });
    },

    deselectAll: function () {
        document.querySelectorAll('.lb-row').forEach(r => r.classList.remove('active'));
    }
};
