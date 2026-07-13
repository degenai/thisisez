window.AURA = window.AURA || {};

window.AURA.Flux = {
    init: function () {
        // Init logic
    },

    update: function (dataContext, assets, isAssetSpecific = false) {
        const canvas = document.getElementById('flux-canvas');
        if (!canvas) return;

        const ctx = canvas.getContext('2d');
        const valueDisplay = document.getElementById('flux-value-display');
        const labelDisplay = document.getElementById('flux-label-display');

        // Metrics Elements
        const greedDisplay = document.getElementById('global-greed');
        const fearDisplay = document.getElementById('global-fear');
        const schizoDisplay = document.getElementById('global-schizo');
        const iqDisplay = document.getElementById('global-iq');
        const chuckleDisplay = document.getElementById('global-chuckle');

        let totalGreed = 0;
        let totalFear = 0;
        let schizoScore = 0;
        let iqScore = 0;
        let chuckleScore = 0;
        let calculatedScore = 50;

        if (isAssetSpecific) {
            // dataContext is the Asset object
            // USE INTENSITY (0-100) for Flux Gauge to match Details Panel
            totalGreed = dataContext.avgGreed || 0;
            totalFear = dataContext.avgFear || 0;
            schizoScore = dataContext.avgSchizo || 0;
            iqScore = dataContext.avgIQ || 0;
            chuckleScore = dataContext.avgChuckle || 0;

            // Calculate Asset Flux based on Intensity
            const total = totalGreed + totalFear;
            if (total > 0) {
                calculatedScore = Math.round((totalGreed / total) * 100);
            } else {
                calculatedScore = 50; // Neutral if no intensity
            }
        } else {
            // Global Mode
            // dataContext is Metadata
            if (dataContext) {
                calculatedScore = dataContext.flux_score || 50;
                schizoScore = dataContext.avg_schizo || 0;
                iqScore = dataContext.avg_iq || 0;
                chuckleScore = dataContext.avg_chuckle || 0;
            }

            // Calculate Total Greed/Fear from assets array for display
            if (Array.isArray(assets)) {
                assets.forEach(a => {
                    totalGreed += a.bullishCount || 0;
                    totalFear += a.bearishCount || 0;
                });
            }
        }

        // Update UI
        if (greedDisplay) greedDisplay.textContent = totalGreed;
        if (fearDisplay) fearDisplay.textContent = totalFear;
        if (schizoDisplay) schizoDisplay.textContent = schizoScore;
        if (iqDisplay) iqDisplay.textContent = iqScore;
        if (chuckleDisplay) chuckleDisplay.textContent = chuckleScore;

        // Draw Gauge
        this.drawGauge(ctx, calculatedScore);

        // Update Text
        if (valueDisplay) valueDisplay.textContent = calculatedScore;

        let label = "NEUTRAL";
        let color = "#fff";

        if (calculatedScore >= 55) { label = "GREED"; color = "var(--c-greed)"; }
        if (calculatedScore >= 75) { label = "EXTREME GREED"; color = "var(--c-greed)"; }
        if (calculatedScore <= 45) { label = "FEAR"; color = "var(--c-fear)"; }
        if (calculatedScore <= 25) { label = "EXTREME FEAR"; color = "var(--c-fear)"; }

        if (isAssetSpecific) {
            label = `ASSET ${label}`;
        }

        if (labelDisplay) {
            labelDisplay.textContent = label;
            labelDisplay.style.color = color;
        }
        if (valueDisplay) valueDisplay.style.color = color;
    },

    drawGauge: function (ctx, score) {
        const w = ctx.canvas.width;
        const h = ctx.canvas.height;
        const cx = w / 2;
        const cy = h - 10;
        const r = w / 2 - 10;

        ctx.clearRect(0, 0, w, h);

        // Background Arc
        ctx.beginPath();
        ctx.arc(cx, cy, r, Math.PI, 0);
        ctx.lineWidth = 15;
        ctx.strokeStyle = "#222";
        ctx.stroke();

        // Value Arc
        const startAngle = Math.PI;
        const endAngle = Math.PI + (Math.PI * (score / 100));

        // Gradient
        const grad = ctx.createLinearGradient(0, h, w, h);
        grad.addColorStop(0, "#ff0000"); // Fear
        grad.addColorStop(0.5, "#ffff00"); // Neutral
        grad.addColorStop(1, "#00ff00"); // Greed

        ctx.beginPath();
        ctx.arc(cx, cy, r, startAngle, endAngle);
        ctx.lineWidth = 15;
        ctx.strokeStyle = grad;
        ctx.stroke();
    }
};
