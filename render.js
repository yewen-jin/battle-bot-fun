import { CONFIG } from './physics.js';

export function createCanvasPair(mountEl) {
  const offCanvas = document.createElement('canvas');
  offCanvas.width = CONFIG.worldW;
  offCanvas.height = CONFIG.worldH;
  const offCtx = offCanvas.getContext('2d');

  const canvas = document.createElement('canvas');
  canvas.width = CONFIG.worldW * CONFIG.pixelScale;
  canvas.height = CONFIG.worldH * CONFIG.pixelScale;
  canvas.style.imageRendering = 'pixelated';
  mountEl.appendChild(canvas);
  const ctx = canvas.getContext('2d');

  return { offCanvas, offCtx, canvas, ctx, arenaImage: null };
}

// Optional arena background — falls back to a flat fill (CONFIG.palette[0])
// in renderFrame() if this never resolves or media/arena.png doesn't exist.
export function loadArenaBackground(pair) {
  const img = new Image();
  img.onload = () => { pair.arenaImage = img; };
  img.src = './media/arena.png';
}

function quantizeAngle(angle) {
  const step = CONFIG.rotationQuantizeDeg;
  const deg = (angle * 180) / Math.PI;
  const snappedDeg = Math.round(deg / step) * step;
  return (snappedDeg * Math.PI) / 180;
}

function drawShadow(offCtx, x, y) {
  const r = CONFIG.botRadius;
  offCtx.fillStyle = CONFIG.shadowColor;
  offCtx.beginPath();
  offCtx.ellipse(x + 1, y + r * 0.6, r * 0.9, r * 0.35, 0, 0, Math.PI * 2);
  offCtx.fill();
}

function drawBody(offCtx, body) {
  const x = Math.round(body.x);
  const y = Math.round(body.y);
  const r = CONFIG.botRadius;

  drawShadow(offCtx, x, y);

  offCtx.save();
  offCtx.translate(x, y);
  offCtx.rotate(quantizeAngle(body.angle));
  offCtx.scale(body.scaleX, body.scaleY);

  if (body.sprite) {
    offCtx.drawImage(body.sprite, -r, -r, r * 2, r * 2);
  } else {
    offCtx.fillStyle = body.color;
    offCtx.beginPath();
    offCtx.arc(0, 0, r, 0, Math.PI * 2);
    offCtx.fill();

    offCtx.lineWidth = 1;
    offCtx.strokeStyle = CONFIG.outlineColor;
    offCtx.stroke();
  }

  drawEyes(offCtx, body);

  offCtx.restore();
}

function drawEyes(offCtx, body) {
  const sockets = [
    { ox: -CONFIG.eyeOffsetX, oy: CONFIG.eyeOffsetY },
    { ox: CONFIG.eyeOffsetX, oy: CONFIG.eyeOffsetY },
  ];

  sockets.forEach((socket, i) => {
    const eye = body.eyes[i];

    offCtx.fillStyle = CONFIG.palette[4];
    offCtx.beginPath();
    offCtx.arc(socket.ox, socket.oy, CONFIG.eyeSocketRadius, 0, Math.PI * 2);
    offCtx.fill();
    offCtx.lineWidth = 0.5;
    offCtx.strokeStyle = CONFIG.outlineColor;
    offCtx.stroke();

    offCtx.fillStyle = CONFIG.outlineColor;
    offCtx.beginPath();
    offCtx.arc(socket.ox + eye.ex, socket.oy + eye.ey, CONFIG.pupilRadius, 0, Math.PI * 2);
    offCtx.fill();
  });
}

function slugify(name) {
  return name.toLowerCase().trim().replace(/[^a-z0-9]+/g, '-').replace(/(^-|-$)/g, '');
}

export function loadSprite(name) {
  return new Promise((resolve) => {
    const img = new Image();
    img.onload = () => resolve(img);
    img.onerror = () => resolve(null);
    img.src = `./media/bots/${slugify(name)}.png`;
  });
}

export function renderFrame({ offCanvas, offCtx, canvas, ctx, arenaImage }, bodies) {
  offCtx.clearRect(0, 0, offCanvas.width, offCanvas.height);
  if (arenaImage) {
    offCtx.drawImage(arenaImage, 0, 0, offCanvas.width, offCanvas.height);
  } else {
    offCtx.fillStyle = CONFIG.palette[0];
    offCtx.fillRect(0, 0, offCanvas.width, offCanvas.height);
  }

  for (const body of bodies) {
    drawBody(offCtx, body);
  }

  ctx.imageSmoothingEnabled = false;
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  ctx.drawImage(
    offCanvas,
    0,
    0,
    offCanvas.width,
    offCanvas.height,
    0,
    0,
    canvas.width,
    canvas.height
  );
}
