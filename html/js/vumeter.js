class VUMeter {
    constructor(width, height, options = {}) {
        this.width = width;
        this.height = height;
        this.currentDb = -60;
        this.targetDb = -60;
        this.peakDb = -60;
        this.peakHoldTime = 0;
        this.clipDetected = false;
        this.isSelected = false;
        this.minDb = options.minDb || -60;
        this.maxDb = options.maxDb || 6;
        this.clipThreshold = options.clipThreshold || 0;
        this.peakHoldDuration = options.peakHoldDuration || 2000; // ms
        this.smoothingFactor = options.smoothingFactor || 0.3;
        this.onClick = options.onClick || undefined;

        // db marker
        this.dbMarkers = [0, -6, -12, -20, -40];

        this.canvas = document.createElement('canvas');
        this.canvas.className = 'mod-vumeter'
        this.canvas.width = width;
        this.canvas.height = height;
        this.canvas.style.width = width;
        this.canvas.style.height = height;
        this.canvas.style.display = 'block';
        this.ctx = this.canvas.getContext('2d');

        this.wrapper = document.createElement('div');
        this.wrapper.className = 'mod-vumeter-wrapper';

        this.clipIndicator = document.createElement('div');
        this.clipIndicator.className = 'mod-vumeter-clip-indicator';
        this.clipIndicator.textContent = 'CLIP';

        this.wrapper.appendChild(this.canvas);
        this.wrapper.appendChild(this.clipIndicator);

        this.canvas.addEventListener('dblclick', (e) => {
            this.resetClip();
            e.stopPropagation();
        });
        this.canvas.addEventListener('click', (e) => {
            if (this.onClick) {
                this.onClick(this, e)
            }
        });

        this.animate();
    }

    getElement() {
        return this.wrapper;
    }

    getLabel() {
        return this.clipIndicator.textContent;
    }

    setLabel(label) {
        this.clipIndicator.textContent = label;
    }

    getLabelIsVisible() {
        return this.clipIndicator.style.display != 'none';
    }

    setLabelIsVisible(visibility) {
        this.clipIndicator.style.display = visibility ? 'unset' : 'none';
    }

    getIsSelected() {
        return this.isSelected;
    }

    setIsSelected(selected) {
        this.isSelected = selected;
    }

    setLevel(db) {
        this.targetDb = Math.max(this.minDb, Math.min(this.maxDb, db));

        if (db >= this.clipThreshold) {
            this.clipDetected = true;
            this.clipIndicator.classList.add('active');
        }

        if (db > this.peakDb) {
            this.peakDb = db;
            this.peakHoldTime = Date.now();
        }
    }

    resetClip() {
        this.clipDetected = false;
        this.clipIndicator.classList.remove('active');
        this.peakDb = this.currentDb;
    }

    dbToHeight(db, h) {
        const borderWidth = 1;
        const availableHeight = (h == undefined ? this.height : h) - (borderWidth * 2);
        const normalized = (db - this.minDb) / (this.maxDb - this.minDb);
        return normalized * availableHeight;
    }

    drawRoundedRect(ctx, x, y, width, height, radius) {
        ctx.beginPath();
        ctx.moveTo(x + radius, y);
        ctx.lineTo(x + width - radius, y);
        ctx.quadraticCurveTo(x + width, y, x + width, y + radius);
        ctx.lineTo(x + width, y + height - radius);
        ctx.quadraticCurveTo(x + width, y + height, x + width - radius, y + height);
        ctx.lineTo(x + radius, y + height);
        ctx.quadraticCurveTo(x, y + height, x, y + height - radius);
        ctx.lineTo(x, y + radius);
        ctx.quadraticCurveTo(x, y, x + radius, y);
        ctx.closePath();
    }

    draw() {
        const w = this.canvas.offsetWidth;
        const h = this.canvas.offsetHeight;
        
        if (isNaN(w) || isNaN(h) || w < 1 || h < 1) {
            // non yet rendered / layout
            return;
        }

        this.canvas.height = h;
        this.canvas.width = w;
        const ctx = this.ctx;
        const borderWidth = 1;

        // Clear
        ctx.clearRect(0, 0, w, h);

        // Background
        ctx.fillStyle = '#0a0a0a';
        ctx.fillRect(0, 0, w, h);

        const barHeight = this.dbToHeight(this.currentDb, h);

        const zeroDbHeight = this.dbToHeight(0, h);
        const barTouchesZeroDb = barHeight >= zeroDbHeight - 1; // -1px tollerance

        if (barHeight > 0) {
            // gradient green -> yellow -> red
            const availableHeight = h - (borderWidth * 2);
            const gradient = ctx.createLinearGradient(0, h - borderWidth, 0, borderWidth);

            const greenHeight = this.dbToHeight(-12, h);
            const yellowHeight = this.dbToHeight(-3, h);
            const redHeight = this.dbToHeight(0, h);

            gradient.addColorStop(0, '#00ff00');
            gradient.addColorStop(Math.min(1, greenHeight / availableHeight), '#00ff00');
            gradient.addColorStop(Math.min(1, yellowHeight / availableHeight), '#ffff00');
            gradient.addColorStop(Math.min(1, redHeight / availableHeight), '#ff3300');
            gradient.addColorStop(1, '#ff0000');

            ctx.fillStyle = gradient;
            ctx.fillRect(
                borderWidth, 
                h - borderWidth - barHeight, 
                w - (borderWidth * 2), 
                barHeight
            );
        }

        // dB scale only if the control is >= 24px wide
        if (w >= 24) {
            ctx.font = '12px monospace';
            ctx.textAlign = 'right';
            ctx.textBaseline = 'middle';

            const labelPadding = 2;
            const labelBgWidth = 18;
            const labelBgHeight = 12;
            const labelBgRadius = 2;

            this.dbMarkers.forEach(db => {
                const markerHeight = this.dbToHeight(db, h);
                const y = h - borderWidth - markerHeight;

                const isAboveBar = markerHeight > barHeight;

                const isZeroDb = db === 0;
                const zeroDbColor = barTouchesZeroDb ? '#ffffff' : '#ff0000';

                ctx.strokeStyle = isZeroDb ? zeroDbColor : '#444';
                ctx.lineWidth = isZeroDb ? 1.5 : 1;
                ctx.beginPath();
                ctx.moveTo(borderWidth, y);
                ctx.lineTo(borderWidth + (w * 0.15), y);
                ctx.stroke();

                const text = db.toString();
                const textX = w - borderWidth - labelPadding;
                const textY = y;

                if (!isAboveBar) {
                    ctx.fillStyle = 'rgba(0, 0, 0, 0.75)';
                    this.drawRoundedRect(
                        ctx,
                        w - borderWidth - labelBgWidth,
                        textY - labelBgHeight / 2,
                        labelBgWidth,
                        labelBgHeight,
                        labelBgRadius
                    );
                    ctx.fill();
                }

                // text
                if (isZeroDb) {
                    // 0dB con outline for better readablity
                    ctx.strokeStyle = '#000';
                    ctx.lineWidth = 2.5;
                    ctx.strokeText(text, textX, textY);
                    ctx.fillStyle = zeroDbColor;
                    ctx.fillText(text, textX, textY);
                } else {
                    ctx.fillStyle = isAboveBar ? '#666' : '#ccc';
                    ctx.fillText(text, textX, textY);
                }
            });
        }

        // 0dB line
        const zeroDbY = h - borderWidth - zeroDbHeight;
        const zeroDbLineColor = barTouchesZeroDb ? 'rgba(255, 255, 255, 0.3)' : 'rgba(255, 0, 0, 0.3)';
        ctx.strokeStyle = zeroDbLineColor;
        ctx.lineWidth = 1;
        ctx.setLineDash([2, 2]);
        ctx.beginPath();
        ctx.moveTo(borderWidth, zeroDbY);
        ctx.lineTo(w - borderWidth, zeroDbY);
        ctx.stroke();
        ctx.setLineDash([]);

        // Peak hold indicator
        const now = Date.now();
        if (now - this.peakHoldTime < this.peakHoldDuration) {
            const peakHeight = this.dbToHeight(this.peakDb, h);
            const peakY = h - borderWidth - peakHeight;

            // Peak color (red when clipping with hold)
            const isClipping = this.peakDb >= this.clipThreshold;
            ctx.fillStyle = isClipping ? '#ff0000' : '#ffffff';

            const peakWidth = w - (borderWidth * 2);

            // Peak line with shadow when clipping
            if (isClipping) {
                ctx.shadowColor = '#ff0000';
                ctx.shadowBlur = 4;
            }

            ctx.fillRect(borderWidth, peakY - 1, peakWidth, 2);

            ctx.shadowBlur = 0;
        } else {
            // peak decay
            this.peakDb = Math.max(this.currentDb, this.peakDb - 0.5);
        }

        // red border when clipping
        ctx.lineWidth = 1;
        if (this.clipDetected) {
            ctx.strokeStyle = '#ff0000';
        } else if (this.isSelected) {
            ctx.strokeStyle = '#883996';
            ctx.lineWidth = 2;
        } else {
            ctx.strokeStyle = '#333';
        }
        ctx.strokeRect(0.5, 0.5, w - 1, h - 1);
    }

    animate() {
        // Smooth interpolation
        this.currentDb += (this.targetDb - this.currentDb) * this.smoothingFactor;

        this.draw();
        requestAnimationFrame(() => this.animate());
    }
}
