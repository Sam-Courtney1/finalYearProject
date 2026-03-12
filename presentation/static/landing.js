/* global requestAnimationFrame */
(function () {
    'use strict';

    // ── Fake donor records (Irish names, Dublin addresses) ──────────────
    const RECORDS = [
        { first_name: "Sarah Murphy", address: "12 Grafton St, Dublin 2", age: 34, blood_type: "O+", organ: "Kidney", consent: true },
        { first_name: "James O'Brien", address: "8 Baggot St Lower, Dublin 2", age: 28, blood_type: "A-", organ: "Liver", consent: true },
        { first_name: "Aoife Kelly", address: "45 Parnell Sq, Dublin 1", age: 41, blood_type: "B+", organ: "Heart", consent: true },
        { first_name: "Ciaran Byrne", address: "3 Camden Row, Dublin 8", age: 55, blood_type: "AB+", organ: "Lung", consent: true },
        { first_name: "Niamh Walsh", address: "67 Merrion Sq, Dublin 2", age: 23, blood_type: "O-", organ: "Pancreas", consent: true },
        { first_name: "Sean Doyle", address: "19 Capel St, Dublin 1", age: 47, blood_type: "A+", organ: "Kidney", consent: true },
        { first_name: "Roisin Brennan", address: "88 Thomas St, Dublin 8", age: 31, blood_type: "B-", organ: "Cornea", consent: true },
        { first_name: "Padraig Ryan", address: "22 Pearse St, Dublin 2", age: 62, blood_type: "AB-", organ: "Liver", consent: true },
        { first_name: "Sinead Flanagan", address: "5 Harcourt Rd, Dublin 2", age: 29, blood_type: "O+", organ: "Heart", consent: true },
        { first_name: "Eoin McCarthy", address: "14 Aungier St, Dublin 2", age: 38, blood_type: "A+", organ: "Lung", consent: true },
        { first_name: "Orla Connolly", address: "31 Dame St, Dublin 2", age: 44, blood_type: "B+", organ: "Kidney", consent: true },
        { first_name: "Declan Hughes", address: "9 Dorset St, Dublin 1", age: 51, blood_type: "O-", organ: "Pancreas", consent: true },
        { first_name: "Aisling Daly", address: "77 Ranelagh Rd, Dublin 6", age: 26, blood_type: "A-", organ: "Cornea", consent: true },
        { first_name: "Cormac Nolan", address: "42 Clanbrassil St, Dublin 8", age: 33, blood_type: "AB+", organ: "Liver", consent: true },
        { first_name: "Maeve Gallagher", address: "56 Rathmines Rd, Dublin 6", age: 39, blood_type: "B-", organ: "Heart", consent: true },
        { first_name: "Fionn Casey", address: "11 Kevin St, Dublin 8", age: 45, blood_type: "O+", organ: "Kidney", consent: true },
        { first_name: "Saoirse Quinn", address: "28 Wexford St, Dublin 2", age: 22, blood_type: "A+", organ: "Lung", consent: true },
        { first_name: "Darragh Moran", address: "63 North Circular Rd, D7", age: 57, blood_type: "AB-", organ: "Pancreas", consent: true },
        { first_name: "Grainne Duffy", address: "4 Mountjoy Sq, Dublin 1", age: 36, blood_type: "B+", organ: "Cornea", consent: true },
        { first_name: "Conor Healy", address: "91 Harold's Cross Rd, D6W", age: 42, blood_type: "O-", organ: "Liver", consent: true },
        { first_name: "Caoimhe Reilly", address: "17 Eccles St, Dublin 7", age: 30, blood_type: "A-", organ: "Heart", consent: true },
        { first_name: "Liam Fitzpatrick", address: "35 Gardiner St, Dublin 1", age: 48, blood_type: "AB+", organ: "Kidney", consent: true },
        { first_name: "Clodagh Power", address: "50 Phibsborough Rd, D7", age: 25, blood_type: "B-", organ: "Lung", consent: true },
        { first_name: "Ronan Kearney", address: "73 South Circular Rd, D8", age: 53, blood_type: "O+", organ: "Pancreas", consent: true },
        { first_name: "Eimear Smyth", address: "6 Leeson St Lower, Dublin 2", age: 27, blood_type: "A+", organ: "Cornea", consent: true },
        { first_name: "Tadhg Murray", address: "38 Inchicore Rd, Dublin 8", age: 60, blood_type: "AB-", organ: "Liver", consent: true },
        { first_name: "Ciara Whelan", address: "21 Drumcondra Rd, Dublin 9", age: 35, blood_type: "B+", organ: "Heart", consent: true },
        { first_name: "Donal Barry", address: "84 Clontarf Rd, Dublin 3", age: 43, blood_type: "O-", organ: "Kidney", consent: true },
        { first_name: "Siobhan Kavanagh", address: "15 Sandymount Ave, Dublin 4", age: 32, blood_type: "A-", organ: "Lung", consent: true },
        { first_name: "Oisin Dempsey", address: "47 Ballsbridge Tce, Dublin 4", age: 50, blood_type: "AB+", organ: "Pancreas", consent: true }
    ];

    const FIELD_ORDER = ['first_name', 'address', 'age', 'blood_type', 'organ', 'consent'];
    // Fields that are NOT encrypted in real pgcrypto DB
    const UNENCRYPTED_FIELDS = new Set(['age', 'consent']);

    // ── Encryption simulation ──────────────────────────────────────────
    function generateEncryptedValue(plaintext) {
        const hex = '0123456789abcdef';
        const len = Math.max(String(plaintext).length * 2, 20);
        let result = '\\xc30d04';
        for (let i = 0; i < len; i++) {
            result += hex[Math.floor(Math.random() * 16)];
        }
        return result;
    }

    // Pre-generate encrypted versions for consistency
    const encryptedCache = [];
    RECORDS.forEach(function (record) {
        const encrypted = {};
        FIELD_ORDER.forEach(function (field) {
            if (UNENCRYPTED_FIELDS.has(field)) {
                encrypted[field] = String(record[field]);
            } else {
                encrypted[field] = generateEncryptedValue(record[field]);
            }
        });
        encryptedCache.push(encrypted);
    });

    // ── State ──────────────────────────────────────────────────────────
    let targetX = -200, targetY = -200;
    let currentX = -200, currentY = -200;
    const isTouch = ('ontouchstart' in window);
    const spotlightRadius = isTouch ? 90 : 130;

    // ── DOM references ─────────────────────────────────────────────────
    let plaintextGrid, encryptedGrid, gridCanvas;
    let gridCtx;
    let invertibles;

    // ── Populate data grids ────────────────────────────────────────────
    function populateDataGrids() {
        plaintextGrid = document.getElementById('data-grid');
        encryptedGrid = document.getElementById('data-grid-encrypted');
        if (!plaintextGrid || !encryptedGrid) return;

        const cols = Math.ceil(window.innerWidth * 1.2 / 220);
        const rows = Math.ceil(window.innerHeight * 1.2 / 44);
        const totalCells = cols * rows;

        let ptHTML = '';
        let encHTML = '';

        for (let i = 0; i < totalCells; i++) {
            const recordIdx = i % RECORDS.length;
            const fieldIdx = (i + Math.floor(i / RECORDS.length)) % FIELD_ORDER.length;
            const field = FIELD_ORDER[fieldIdx];
            const record = RECORDS[recordIdx];
            const encRecord = encryptedCache[recordIdx];

            const ptValue = String(record[field]);
            const encValue = encRecord[field];

            ptHTML += '<div class="data-cell"><span class="data-cell__label">' +
                field + ': </span>' + ptValue + '</div>';
            encHTML += '<div class="data-cell"><span class="data-cell__label">' +
                field + ': </span>' + encValue + '</div>';
        }

        plaintextGrid.innerHTML = ptHTML;
        encryptedGrid.innerHTML = encHTML;
    }

    // ── Resize canvases ────────────────────────────────────────────────
    function resizeCanvases() {
        gridCanvas = document.getElementById('grid-canvas');
        if (!gridCanvas) return;

        const w = window.innerWidth;
        const h = window.innerHeight;
        const dpr = window.devicePixelRatio || 1;

        gridCanvas.width = w * dpr;
        gridCanvas.height = h * dpr;
        gridCanvas.style.width = w + 'px';
        gridCanvas.style.height = h + 'px';
        gridCtx = gridCanvas.getContext('2d');
        gridCtx.scale(dpr, dpr);
    }

    // ── Spotlight (clip-path on encrypted layer) ───────────────────────
    function updateSpotlight() {
        if (!encryptedGrid) return;
        encryptedGrid.style.setProperty('--spotlight-x', currentX + 'px');
        encryptedGrid.style.setProperty('--spotlight-y', currentY + 'px');
    }


    // ── Animated grid lines ────────────────────────────────────────────
    let gridFrameCount = 0;

    function drawGrid() {
        if (!gridCtx) return;
        gridFrameCount++;
        // Throttle to ~30fps
        if (gridFrameCount % 2 !== 0) return;

        const w = window.innerWidth;
        const h = window.innerHeight;
        gridCtx.clearRect(0, 0, w, h);

        const spacing = 60;

        gridCtx.lineWidth = 0.5;
        // Vertical lines
        for (let x = 0; x < w; x += spacing) {
            const distX = Math.abs(x - currentX);
            const brightness = Math.max(0.03, 0.12 - distX / 900);
            gridCtx.strokeStyle = 'rgba(124, 58, 237, ' + brightness + ')';
            gridCtx.beginPath();
            gridCtx.moveTo(x, 0);
            gridCtx.lineTo(x, h);
            gridCtx.stroke();
        }
        // Horizontal lines
        for (let y = 0; y < h; y += spacing) {
            const distY = Math.abs(y - currentY);
            const brightness2 = Math.max(0.03, 0.12 - distY / 900);
            gridCtx.strokeStyle = 'rgba(124, 58, 237, ' + brightness2 + ')';
            gridCtx.beginPath();
            gridCtx.moveTo(0, y);
            gridCtx.lineTo(w, y);
            gridCtx.stroke();
        }

        // Glow at cursor intersection
        if (currentX > 0 && currentY > 0) {
            const gradient = gridCtx.createRadialGradient(
                currentX, currentY, 0,
                currentX, currentY, 200
            );
            gradient.addColorStop(0, 'rgba(124, 58, 237, 0.06)');
            gradient.addColorStop(1, 'rgba(124, 58, 237, 0)');
            gridCtx.fillStyle = gradient;
            gridCtx.fillRect(0, 0, w, h);
        }
    }

    // ── Parallax ───────────────────────────────────────────────────────
    function updateParallax() {
        const parallaxEls = document.querySelectorAll('[data-parallax-speed]');
        if (!parallaxEls.length) return;

        const cx = window.innerWidth / 2;
        const cy = window.innerHeight / 2;
        const dx = (currentX - cx) / cx || 0;
        const dy = (currentY - cy) / cy || 0;

        for (let i = 0; i < parallaxEls.length; i++) {
            const el = parallaxEls[i];
            const speed = parseFloat(el.dataset.parallaxSpeed) || 0;
            const moveX = dx * speed * -30;
            const moveY = dy * speed * -30;
            el.style.transform = 'translate(' + moveX + 'px, ' + moveY + 'px)';
        }
    }

    // ── Text inversion ─────────────────────────────────────────────────
    function updateInversion() {
        if (!invertibles) return;

        for (let i = 0; i < invertibles.length; i++) {
            const el = invertibles[i];
            const rect = el.getBoundingClientRect();
            const elCx = rect.left + rect.width / 2;
            const elCy = rect.top + rect.height / 2;
            const dist = Math.hypot(elCx - currentX, elCy - currentY);

            if (dist < spotlightRadius + Math.max(rect.width, rect.height) / 2) {
                el.classList.add('landing--inverted');
            } else {
                el.classList.remove('landing--inverted');
            }
        }
    }

    // ── Data grid parallax (subtle shift) ──────────────────────────────
    function updateGridParallax() {
        if (!plaintextGrid || !encryptedGrid) return;
        const cx = window.innerWidth / 2;
        const cy = window.innerHeight / 2;
        const dx = (currentX - cx) / cx || 0;
        const dy = (currentY - cy) / cy || 0;

        const offsetX = -10 + dx * -1.5;
        const offsetY = -10 + dy * -1.5;
        const transform = 'translate(' + offsetX + '%, ' + offsetY + '%)';
        plaintextGrid.style.transform = transform;
        encryptedGrid.style.transform = transform;
    }

    // ── Main animation loop ────────────────────────────────────────────
    function mainLoop() {
        // Lerp cursor position (smooth follow with delay)
        currentX += (targetX - currentX) * 0.1;
        currentY += (targetY - currentY) * 0.1;

        updateSpotlight();
        drawGrid();
        updateParallax();
        updateInversion();
        updateGridParallax();

        requestAnimationFrame(mainLoop);
    }

    // ── Event listeners ────────────────────────────────────────────────
    function onMouseMove(e) {
        targetX = e.clientX;
        targetY = e.clientY;
    }

    function onTouchMove(e) {
        if (e.touches.length > 0) {
            targetX = e.touches[0].clientX;
            targetY = e.touches[0].clientY;
        }
    }

    function onTouchEnd() {
        // Move spotlight off screen when not touching
        targetX = -200;
        targetY = -200;
    }

    // ── Init ───────────────────────────────────────────────────────────
    document.addEventListener('DOMContentLoaded', function () {
        populateDataGrids();
        resizeCanvases();
        invertibles = document.querySelectorAll('[data-invertible]');

        if (isTouch) {
            document.addEventListener('touchmove', onTouchMove, { passive: true });
            document.addEventListener('touchend', onTouchEnd);
        } else {
            document.addEventListener('mousemove', onMouseMove);
        }

        window.addEventListener('resize', function () {
            resizeCanvases();
            populateDataGrids();
        });

        mainLoop();
    });
})();
