/**
 * HemoNexus Signature ECG Heartbeat Background Animation
 * 
 * Renders a continuous, subtle medical ECG heartbeat wave across the EXACT CENTER of the viewport.
 * Features realistic P-Q-R-S-T heartbeat spikes, glowing traveling pulse, and crimson gradient aesthetics.
 * Preserves 60fps performance, pointer-events: none, and WCAG accessibility.
 */

(function () {
  'use strict';

  // Check reduced motion preference
  const motionQuery = window.matchMedia('(prefers-reduced-motion: reduce)');
  let isReducedMotion = motionQuery.matches;

  // Create or reuse background canvas
  let canvas = document.getElementById('network-bg');
  if (!canvas) {
    canvas = document.createElement('canvas');
    canvas.id = 'network-bg';
    canvas.setAttribute('aria-hidden', 'true');
    canvas.style.cssText = 'position:fixed;top:0;left:0;width:100vw;height:100vh;z-index:0;pointer-events:none;';
    document.body.prepend(canvas);
  }

  const ctx = canvas.getContext('2d', { alpha: true });
  let w = 0;
  let h = 0;
  let dpr = 1;
  let animFrameId = null;

  // ECG Waveform parameters
  let offset = 0;
  const speed = 1.3; // Horizontal movement speed

  function resize() {
    w = window.innerWidth;
    h = window.innerHeight;
    dpr = Math.min(window.devicePixelRatio || 1, 2);
    canvas.width = Math.floor(w * dpr);
    canvas.height = Math.floor(h * dpr);
    ctx.scale(dpr, dpr);

    if (isReducedMotion) {
      drawStatic();
    }
  }

  motionQuery.addEventListener('change', (e) => {
    isReducedMotion = e.matches;
    if (isReducedMotion) {
      if (animFrameId) cancelAnimationFrame(animFrameId);
      drawStatic();
    } else {
      render();
    }
  });

  window.addEventListener('resize', resize, { passive: true });
  resize();

  /**
   * Evaluates the Y offset for a given X coordinate along an ECG heartbeat cycle.
   * Pattern length = 340px for large, clearly recognizable heartbeat spike
   */
  function getEcgY(x, baseY) {
    const patternWidth = 340;
    const pos = (x % patternWidth + patternWidth) % patternWidth;

    // Flat baseline default
    if (pos < 130 || pos > 250) {
      return baseY;
    }

    // P-Wave (Small bump up)
    if (pos >= 130 && pos < 150) {
      const t = (pos - 130) / 20;
      return baseY - Math.sin(t * Math.PI) * 9;
    }

    // PR Segment
    if (pos >= 150 && pos < 165) {
      return baseY;
    }

    // Q Spike (Small dip down)
    if (pos >= 165 && pos < 172) {
      const t = (pos - 165) / 7;
      return baseY + Math.sin(t * Math.PI) * 10;
    }

    // R Spike (TALL Sharp Heartbeat Peak - 60px height)
    if (pos >= 172 && pos < 184) {
      const t = (pos - 172) / 12;
      return baseY - Math.sin(t * Math.PI) * 62;
    }

    // S Spike (Sharp Deep Dip Down - 26px depth)
    if (pos >= 184 && pos < 194) {
      const t = (pos - 184) / 10;
      return baseY + Math.sin(t * Math.PI) * 26;
    }

    // ST Segment
    if (pos >= 194 && pos < 205) {
      return baseY;
    }

    // T-Wave (Medium Recovery Bump)
    if (pos >= 205 && pos < 235) {
      const t = (pos - 205) / 30;
      return baseY - Math.sin(t * Math.PI) * 15;
    }

    return baseY;
  }

  function drawEcgLine(baseY, lineOffset, alphaMultiplier = 1) {
    ctx.beginPath();
    const step = 3;
    let first = true;

    for (let x = -20; x <= w + 20; x += step) {
      const y = getEcgY(x + lineOffset, baseY);
      if (first) {
        ctx.moveTo(x, y);
        first = false;
      } else {
        ctx.lineTo(x, y);
      }
    }

    ctx.strokeStyle = `rgba(200, 30, 58, ${0.16 * alphaMultiplier})`;
    ctx.lineWidth = 1.9;
    ctx.stroke();
  }

  function drawGlowingPulse(baseY, lineOffset) {
    const pulseX = (offset * 2.6) % (w + 240) - 120;
    const pulseY = getEcgY(pulseX + lineOffset, baseY);

    ctx.save();
    ctx.beginPath();
    ctx.arc(pulseX, pulseY, 3.8, 0, Math.PI * 2);
    ctx.fillStyle = 'rgba(200, 30, 58, 0.9)';
    ctx.shadowColor = 'rgba(200, 30, 58, 0.95)';
    ctx.shadowBlur = 14;
    ctx.fill();

    // Pulse Tail Stroke
    ctx.beginPath();
    const tailLen = 70;
    for (let dx = 0; dx <= tailLen; dx += 2) {
      const tx = pulseX - dx;
      const ty = getEcgY(tx + lineOffset, baseY);
      if (dx === 0) ctx.moveTo(tx, ty);
      else ctx.lineTo(tx, ty);
    }
    const gradient = ctx.createLinearGradient(pulseX, 0, pulseX - tailLen, 0);
    gradient.addColorStop(0, 'rgba(200, 30, 58, 0.7)');
    gradient.addColorStop(1, 'rgba(200, 30, 58, 0)');
    ctx.strokeStyle = gradient;
    ctx.lineWidth = 2.4;
    ctx.stroke();
    ctx.restore();
  }

  function drawStatic() {
    ctx.clearRect(0, 0, w, h);
    // Primary baseline ECG centered at EXACT VERTICAL CENTER (h * 0.50)
    drawEcgLine(h * 0.50, 0, 1.2);
  }

  function render() {
    if (isReducedMotion) {
      drawStatic();
      return;
    }

    offset += speed;
    ctx.clearRect(0, 0, w, h);

    // Primary ECG Line positioned at EXACT VERTICAL CENTER (h * 0.50)
    const centerY = h * 0.50;
    drawEcgLine(centerY, -offset, 1.3);
    drawGlowingPulse(centerY, -offset);

    animFrameId = requestAnimationFrame(render);
  }

  render();
})();
