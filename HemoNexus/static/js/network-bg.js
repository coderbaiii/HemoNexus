/**
 * HemoNexus Subtle Blood-Flow & Live Network Background Canvas
 * 
 * Renders extremely low-opacity flowing curved blood vessel paths and
 * ambient network nodes behind the white healthcare interface.
 * Preserves high performance, 60fps smoothness, and WCAG accessibility.
 */

(function () {
  'use strict';

  // Check reduced motion preference
  const motionQuery = window.matchMedia('(prefers-reduced-motion: reduce)');
  let isReducedMotion = motionQuery.matches;

  motionQuery.addEventListener('change', (e) => {
    isReducedMotion = e.matches;
    if (!isReducedMotion && !animFrameId) {
      animFrameId = requestAnimationFrame(render);
    }
  });

  // Create or reuse background canvas
  let canvas = document.getElementById('network-bg');
  if (!canvas) {
    canvas = document.createElement('canvas');
    canvas.id = 'network-bg';
    canvas.setAttribute('aria-hidden', 'true');
    canvas.style.cssText = 'position:fixed;top:0;left:0;width:100%;height:100%;z-index:0;pointer-events:none;';
    document.body.prepend(canvas);
  }

  const ctx = canvas.getContext('2d', { alpha: true });
  let w = 0;
  let h = 0;
  let dpr = window.devicePixelRatio || 1;
  let animFrameId = null;

  // Nodes & Flow lines state
  const NODE_COUNT = 24;
  const nodes = [];
  let pulses = [];
  let time = 0;

  // Flowing Blood Vessel Curves (Crimson & Teal streams)
  const vessels = [
    { yRatio: 0.18, amp: 40, freq: 0.0012, speed: 0.0006, color: 'rgba(200, 30, 58, 0.04)', width: 2 },
    { yRatio: 0.38, amp: 55, freq: 0.0009, speed: 0.0004, color: 'rgba(14, 124, 107, 0.035)', width: 2.5 },
    { yRatio: 0.62, amp: 45, freq: 0.0014, speed: 0.0005, color: 'rgba(200, 30, 58, 0.035)', width: 1.8 },
    { yRatio: 0.85, amp: 60, freq: 0.0008, speed: 0.0003, color: 'rgba(14, 124, 107, 0.03)', width: 2 }
  ];

  function resize() {
    w = window.innerWidth;
    h = window.innerHeight;
    dpr = Math.min(window.devicePixelRatio || 1, 2);
    canvas.width = Math.floor(w * dpr);
    canvas.height = Math.floor(h * dpr);
    ctx.scale(dpr, dpr);

    // Initialize nodes if empty or re-clamp positions
    if (nodes.length === 0) {
      for (let i = 0; i < NODE_COUNT; i++) {
        nodes.push({
          x: Math.random() * w,
          y: Math.random() * h,
          vx: (Math.random() - 0.5) * 0.22,
          vy: (Math.random() - 0.5) * 0.22,
          radius: 1.8 + Math.random() * 1.6,
          isTeal: i % 3 === 0
        });
      }
    } else {
      nodes.forEach(n => {
        if (n.x > w) n.x = w - 10;
        if (n.y > h) n.y = h - 10;
      });
    }

    if (isReducedMotion) {
      drawStatic();
    }
  }

  window.addEventListener('resize', resize, { passive: true });
  resize();

  function maybeSpawnPulse() {
    if (pulses.length < 5 && Math.random() < 0.03 && nodes.length > 1) {
      const idxA = Math.floor(Math.random() * nodes.length);
      const nodeA = nodes[idxA];
      
      // Find a close neighbor
      for (let j = 0; j < nodes.length; j++) {
        if (j !== idxA) {
          const nodeB = nodes[j];
          const dx = nodeA.x - nodeB.x;
          const dy = nodeA.y - nodeB.y;
          const dist = Math.sqrt(dx * dx + dy * dy);
          if (dist > 40 && dist < 190) {
            pulses.push({
              a: nodeA,
              b: nodeB,
              t: 0,
              speed: 0.012 + Math.random() * 0.01,
              isTeal: nodeA.isTeal || nodeB.isTeal
            });
            break;
          }
        }
      }
    }
  }

  function drawVesselCurves() {
    vessels.forEach(v => {
      ctx.beginPath();
      ctx.strokeStyle = v.color;
      ctx.lineWidth = v.width;
      ctx.lineCap = 'round';

      const baseY = h * v.yRatio;
      ctx.moveTo(0, baseY + Math.sin(time * v.speed) * v.amp);

      const steps = 12;
      const stepX = w / steps;
      for (let s = 1; s <= steps; s++) {
        const x = s * stepX;
        const prevX = (s - 1) * stepX;
        const cx = (prevX + x) / 2;
        const cy = baseY + Math.sin(prevX * v.freq + time * v.speed) * v.amp;
        const y = baseY + Math.sin(x * v.freq + time * v.speed) * v.amp;
        ctx.quadraticCurveTo(prevX, cy, x, y);
      }
      ctx.stroke();
    });
  }

  function drawStatic() {
    ctx.clearRect(0, 0, w, h);
    drawVesselCurves();

    // Subtle faint nodes
    nodes.forEach(n => {
      ctx.fillStyle = n.isTeal ? 'rgba(14, 124, 107, 0.12)' : 'rgba(200, 30, 58, 0.12)';
      ctx.beginPath();
      ctx.arc(n.x, n.y, n.radius, 0, Math.PI * 2);
      ctx.fill();
    });

    // Faint connection mesh
    for (let i = 0; i < nodes.length; i++) {
      for (let j = i + 1; j < nodes.length; j++) {
        const dx = nodes[i].x - nodes[j].x;
        const dy = nodes[i].y - nodes[j].y;
        const dist = Math.sqrt(dx * dx + dy * dy);
        if (dist < 160) {
          const alpha = 0.04 * (1 - dist / 160);
          ctx.strokeStyle = `rgba(200, 30, 58, ${alpha})`;
          ctx.lineWidth = 0.8;
          ctx.beginPath();
          ctx.moveTo(nodes[i].x, nodes[i].y);
          ctx.lineTo(nodes[j].x, nodes[j].y);
          ctx.stroke();
        }
      }
    }
  }

  function render() {
    if (isReducedMotion) {
      drawStatic();
      animFrameId = null;
      return;
    }

    time += 1;
    ctx.clearRect(0, 0, w, h);

    // 1. Draw flowing organic blood-vessel curves
    drawVesselCurves();

    // 2. Update and draw nodes
    nodes.forEach(n => {
      n.x += n.vx;
      n.y += n.vy;
      if (n.x < 10 || n.x > w - 10) n.vx *= -1;
      if (n.y < 10 || n.y > h - 10) n.vy *= -1;
    });

    // 3. Draw connection lines
    for (let i = 0; i < nodes.length; i++) {
      for (let j = i + 1; j < nodes.length; j++) {
        const dx = nodes[i].x - nodes[j].x;
        const dy = nodes[i].y - nodes[j].y;
        const dist = Math.sqrt(dx * dx + dy * dy);
        if (dist < 180) {
          const alpha = 0.055 * (1 - dist / 180);
          ctx.strokeStyle = nodes[i].isTeal || nodes[j].isTeal
            ? `rgba(14, 124, 107, ${alpha * 0.9})`
            : `rgba(200, 30, 58, ${alpha})`;
          ctx.lineWidth = 0.9;
          ctx.beginPath();
          ctx.moveTo(nodes[i].x, nodes[i].y);
          ctx.lineTo(nodes[j].x, nodes[j].y);
          ctx.stroke();
        }
      }
    }

    // 4. Draw node dots
    nodes.forEach(n => {
      ctx.fillStyle = n.isTeal ? 'rgba(14, 124, 107, 0.16)' : 'rgba(200, 30, 58, 0.16)';
      ctx.beginPath();
      ctx.arc(n.x, n.y, n.radius, 0, Math.PI * 2);
      ctx.fill();
    });

    // 5. Update & draw traveling data/blood pulses
    maybeSpawnPulse();
    for (let p = pulses.length - 1; p >= 0; p--) {
      const pulse = pulses[p];
      pulse.t += pulse.speed;
      if (pulse.t >= 1) {
        pulses.splice(p, 1);
        continue;
      }
      const px = pulse.a.x + (pulse.b.x - pulse.a.x) * pulse.t;
      const py = pulse.a.y + (pulse.b.y - pulse.a.y) * pulse.t;

      ctx.fillStyle = pulse.isTeal ? 'rgba(14, 124, 107, 0.55)' : 'rgba(200, 30, 58, 0.55)';
      ctx.beginPath();
      ctx.arc(px, py, 2.5, 0, Math.PI * 2);
      ctx.fill();
    }

    animFrameId = requestAnimationFrame(render);
  }

  render();
})();
