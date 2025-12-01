window.AURA = window.AURA || {};

window.AURA.Details = {
    init: function () {
        // Init logic
    },

    show: function (asset) {
        const container = document.getElementById('details-view');
        const status = document.getElementById('details-status');

        if (status) {
            status.innerHTML = `VIEWING: ${asset.name} <span id="clear-selection" style="cursor:pointer; color:#666; margin-left:5px">[X]</span>`;
            status.style.color = "var(--c-primary)";

            // Bind Clear Event
            const clearBtn = document.getElementById('clear-selection');
            if (clearBtn) {
                clearBtn.onclick = (e) => {
                    e.stopPropagation();
                    window.AURA.App.clearSelection();
                };
            }
        }

        // Split Narratives
        const bullish = asset.narratives.filter(n => n.sentiment === 'BULLISH');
        const bearish = asset.narratives.filter(n => n.sentiment === 'BEARISH');

        // Render
        if (container) {
            container.innerHTML = `
                <div class="details-container">
                    <div class="asset-header">
                        <div class="asset-title">${asset.name}</div>
                        <div class="asset-meta" style="color: var(--c-text-dim)">VOL: ${asset.count}</div>
                    </div>

                    <div class="asset-metrics-grid">
                        <div class="metric-card">
                            <span class="metric-label">NET SENTIMENT</span>
                            <span class="metric-val" style="color: ${asset.netScore >= 0 ? 'var(--c-greed)' : 'var(--c-fear)'}">${asset.netScore}</span>
                        </div>
                        <div class="metric-card">
                            <span class="metric-label">GREED/FEAR</span>
                            <span class="metric-val">
                                <span style="color:var(--c-greed)">${asset.avgGreed || 0}</span>/<span style="color:var(--c-fear)">${asset.avgFear || 0}</span>
                            </span>
                        </div>
                    </div>

                    <div class="narrative-section">
                        <div class="thesis-col thesis-bullish">
                            <h3>BULLISH THESIS (${bullish.length})</h3>
                            <ul class="narrative-list">
                                ${bullish.length ? bullish.map(n => `
                                    <li>
                                        <div style="margin-bottom:4px">${n.text}</div>
                                        <div style="font-size:10px; color:#666">REF: ${n.thread_sub.substring(0, 30)}...</div>
                                    </li>
                                `).join('') : '<li style="color:#444; font-style:italic">NO SIGNAL</li>'}
                            </ul>
                        </div>

                        <div class="thesis-col thesis-bearish">
                            <h3>BEARISH THESIS (${bearish.length})</h3>
                            <ul class="narrative-list">
                                ${bearish.length ? bearish.map(n => `
                                    <li>
                                        <div style="margin-bottom:4px">${n.text}</div>
                                        <div style="font-size:10px; color:#666">REF: ${n.thread_sub.substring(0, 30)}...</div>
                                    </li>
                                `).join('') : '<li style="color:#444; font-style:italic">NO SIGNAL</li>'}
                            </ul>
                        </div>
                    </div>

                    ${asset.bestQuote ? `
                        <div class="quote-box">
                            "${asset.bestQuote}"
                        </div>
                    ` : ''}
                </div>
            `;
        }
    },

    clear: function () {
        const container = document.getElementById('details-view');
        const status = document.getElementById('details-status');

        if (status) {
            status.textContent = "WAITING FOR SELECTION...";
            status.style.color = "var(--c-text-dim)";
        }

        if (container) {
            container.innerHTML = `
                <div class="empty-state">
                    <div class="ascii-logo">
                        ▄▄▄ █ ██ ██▀███ ▄▄▄
                        ▒████▄ ██ ▓██▒▓██ ▒ ██▒▒████▄
                        ▒██ ▀█▄ ▓██ ▒██░▓██ ░▄█ ▒▒██ ▀█▄
                        ░██▄▄▄▄██ ▓▓█ ░██░▒██▀▀█▄ ░██▄▄▄▄██
                        ▓█ ▓██▒▒▒█████▓ ░██▓ ▒██▒ ▓█ ▓██▒
                        ▒▒ ▓▒█░░▒▓▒ ▒ ▒ ░ ▒▓ ░▒▓░ ▒▒ ▓▒█░
                    </div>
                    <p>SELECT AN ASSET TO DECODE NARRATIVE</p>
                </div>
            `;
        }
    }
};
