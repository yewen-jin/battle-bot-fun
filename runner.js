import { applyImpulse, snapToContact, step, FIXED_DT, CONFIG } from './physics.js';
import { renderFrame } from './render.js';

function speak(line) {
  if (typeof window.speak === 'function') {
    window.speak(line);
  }
}

export function runFight(fight, bodies, targetMap, canvasPair, captionEl) {
  const beats = fight.beats;
  let elapsed = 0;
  let speakIdx = 0;
  let impulseIdx = 0;
  let shakeMagnitude = 0;

  let accumulator = 0;
  let renderAccumulator = 0;
  let last = performance.now();
  let stopped = false;

  function frame(now) {
    if (stopped) return;
    const dt = Math.min((now - last) / 1000, 0.25);
    last = now;
    accumulator += dt;

    while (accumulator >= FIXED_DT) {
      while (speakIdx < beats.length && beats[speakIdx].t - CONFIG.speakLeadSeconds <= elapsed) {
        const beat = beats[speakIdx];
        speak(beat.line);
        if (captionEl) {
          captionEl.textContent = beat.fact ? `${beat.line}\n${beat.fact}` : beat.line;
        }
        speakIdx++;
      }

      while (impulseIdx < beats.length && beats[impulseIdx].t <= elapsed) {
        const beat = beats[impulseIdx];
        if (bodies.length === 2) snapToContact(bodies[0], bodies[1]);
        for (const body of targetMap[beat.target]) {
          applyImpulse(body, beat.impulse, beat.spin);
        }
        shakeMagnitude = Math.max(shakeMagnitude, beat.shake * CONFIG.cameraShakeMax);
        impulseIdx++;
      }

      step(bodies, FIXED_DT);
      shakeMagnitude *= Math.exp(-CONFIG.cameraShakeDecayRate * FIXED_DT);
      elapsed += FIXED_DT;
      accumulator -= FIXED_DT;
    }

    renderAccumulator += dt;
    if (renderAccumulator >= 1 / CONFIG.renderFps) {
      renderAccumulator = 0;
      renderFrame(canvasPair, bodies);
      const dx = (Math.random() * 2 - 1) * shakeMagnitude;
      const dy = (Math.random() * 2 - 1) * shakeMagnitude;
      canvasPair.canvas.style.transform = `translate(${dx.toFixed(1)}px, ${dy.toFixed(1)}px)`;
    }

    requestAnimationFrame(frame);
  }
  requestAnimationFrame(frame);

  return {
    stop() { stopped = true; },
  };
}
