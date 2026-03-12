/* global requestAnimationFrame */
(function () {
    'use strict';

    let canvas, ctx;
    let particles = [];
    let mouseX = -1, mouseY = -1;
    const PARTICLE_COUNT = 60;
    const MAX_DIST = 120;

    function Particle(w, h) {
        this.x = Math.random() * w;
        this.y = Math.random() * h;
        this.vx = (Math.random() - 0.5) * 0.4;
        this.vy = (Math.random() - 0.5) * 0.4;
        this.radius = Math.random() * 1.5 + 0.5;
        this.opacity = Math.random() * 0.3 + 0.1;
    }

    function initCanvas() {
        canvas = document.getElementById('cl-particles');
        if (!canvas) return;

        const dpr = window.devicePixelRatio || 1;
        const w = window.innerWidth;
        const h = window.innerHeight;

        canvas.width = w * dpr;
        canvas.height = h * dpr;
        canvas.style.width = w + 'px';
        canvas.style.height = h + 'px';

        ctx = canvas.getContext('2d');
        ctx.scale(dpr, dpr);

        particles = [];
        for (let i = 0; i < PARTICLE_COUNT; i++) {
            particles.push(new Particle(w, h));
        }
    }

    function animate() {
        if (!ctx) return;

        const w = window.innerWidth;
        const h = window.innerHeight;
        ctx.clearRect(0, 0, w, h);

        for (let i = 0; i < particles.length; i++) {
            const p = particles[i];

            if (mouseX > 0 && mouseY > 0) {
                const dx = p.x - mouseX;
                const dy = p.y - mouseY;
                const dist = Math.sqrt(dx * dx + dy * dy);
                if (dist < 150) {
                    const force = (150 - dist) / 150 * 0.008;
                    p.vx += dx * force;
                    p.vy += dy * force;
                }
            }

            p.vx *= 0.99;
            p.vy *= 0.99;
            p.x += p.vx;
            p.y += p.vy;

            if (p.x < 0) p.x = w;
            if (p.x > w) p.x = 0;
            if (p.y < 0) p.y = h;
            if (p.y > h) p.y = 0;

            ctx.beginPath();
            ctx.arc(p.x, p.y, p.radius, 0, Math.PI * 2);
            ctx.fillStyle = 'rgba(255, 255, 255, ' + p.opacity + ')';
            ctx.fill();
        }

        ctx.lineWidth = 0.5;
        for (let i = 0; i < particles.length; i++) {
            for (let j = i + 1; j < particles.length; j++) {
                const dx = particles[i].x - particles[j].x;
                const dy = particles[i].y - particles[j].y;
                const dist = Math.sqrt(dx * dx + dy * dy);

                if (dist < MAX_DIST) {
                    const alpha = (1 - dist / MAX_DIST) * 0.08;
                    ctx.beginPath();
                    ctx.moveTo(particles[i].x, particles[i].y);
                    ctx.lineTo(particles[j].x, particles[j].y);
                    ctx.strokeStyle = 'rgba(124, 58, 237, ' + alpha + ')';
                    ctx.stroke();
                }
            }
        }

        requestAnimationFrame(animate);
    }

    document.addEventListener('DOMContentLoaded', function () {
        initCanvas();
        animate();

        document.addEventListener('mousemove', function (e) {
            mouseX = e.clientX;
            mouseY = e.clientY;
        });

        window.addEventListener('resize', initCanvas);
    });
})();
