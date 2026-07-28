export const CONFIG = {
  worldW: 160, worldH: 90,
  floorY: 78, wallLeft: 8, wallRight: 152,
  gravity: 420,
  floorRestitution: 0.55, wallRestitution: 0.60,
  groundDampingLinear: 0.82, groundDampingAngular: 0.70,
  botRadius: 7,
  rotationQuantizeDeg: 15,
  pixelScale: 8,
  palette: ['#1a1a2e', '#e94560', '#0f3460', '#16213e', '#f5f5f5', '#ffd460', '#533483', '#0a0a0a'],
  outlineColor: '#0a0a0a',
  shadowColor: 'rgba(0,0,0,0.35)',
  eyeStiffness: 90,
  eyeDamping: 10,
  eyeAccelGain: 0.02,
  eyeClampRadius: 2.2,
  eyeSocketRadius: 2.6,
  pupilRadius: 1.1,
  eyeOffsetX: 3.0,
  eyeOffsetY: -3.0,
  squashCoefficient: 0.0025,
  squashMax: 0.6,
  squashDecayRate: 12,
  cameraShakeMax: 16,
  cameraShakeDecayRate: 10,
  speakLeadSeconds: 0.15,
  renderFps: 12,
}

export const FIXED_DT = 1 / 60

function createEye() {
  return { ex: 0, ey: 0, evx: 0, evy: 0 }
}

export function createBody(x, y, color) {
  return {
    x, y, vx: 0, vy: 0, angle: 0, av: 0, scaleX: 1, scaleY: 1, color,
    eyes: [createEye(), createEye()],
    squash: 0, squashAxis: 'y',
  }
}

export function applyImpulse(body, impulse, spin) {
  body.vx += impulse.x
  body.vy += impulse.y
  body.av += spin
}

function updateEye(eye, localAx, localAy, dt) {
  eye.evx += (-CONFIG.eyeStiffness * eye.ex - CONFIG.eyeDamping * eye.evx - CONFIG.eyeAccelGain * localAx) * dt
  eye.evy += (-CONFIG.eyeStiffness * eye.ey - CONFIG.eyeDamping * eye.evy - CONFIG.eyeAccelGain * localAy) * dt
  eye.ex += eye.evx * dt
  eye.ey += eye.evy * dt

  const dist = Math.hypot(eye.ex, eye.ey)
  if (dist > CONFIG.eyeClampRadius) {
    const k = CONFIG.eyeClampRadius / dist
    eye.ex *= k
    eye.ey *= k
    eye.evx = 0
    eye.evy = 0
  }
}

function stepBody(body, dt) {
  const prevVx = body.vx
  const prevVy = body.vy

  body.vy += CONFIG.gravity * dt

  body.x += body.vx * dt
  body.y += body.vy * dt
  body.angle += body.av * dt

  if (body.y + CONFIG.botRadius > CONFIG.floorY) {
    const impactSpeed = Math.abs(body.vy)
    body.y = CONFIG.floorY - CONFIG.botRadius
    body.vy *= -CONFIG.floorRestitution
    body.vx *= CONFIG.groundDampingLinear
    body.av *= CONFIG.groundDampingAngular
    body.squash = Math.min(CONFIG.squashCoefficient * impactSpeed, CONFIG.squashMax)
    body.squashAxis = 'y'
  }

  if (body.x - CONFIG.botRadius < CONFIG.wallLeft) {
    const impactSpeed = Math.abs(body.vx)
    body.x = CONFIG.wallLeft + CONFIG.botRadius
    body.vx *= -CONFIG.wallRestitution
    body.squash = Math.min(CONFIG.squashCoefficient * impactSpeed, CONFIG.squashMax)
    body.squashAxis = 'x'
  } else if (body.x + CONFIG.botRadius > CONFIG.wallRight) {
    const impactSpeed = Math.abs(body.vx)
    body.x = CONFIG.wallRight - CONFIG.botRadius
    body.vx *= -CONFIG.wallRestitution
    body.squash = Math.min(CONFIG.squashCoefficient * impactSpeed, CONFIG.squashMax)
    body.squashAxis = 'x'
  }

  body.squash *= Math.exp(-CONFIG.squashDecayRate * dt)
  if (body.squash < 0.001) {
    body.squash = 0
    body.scaleX = 1
    body.scaleY = 1
  } else if (body.squashAxis === 'y') {
    body.scaleY = 1 - body.squash
    body.scaleX = 1 / body.scaleY
  } else {
    body.scaleX = 1 - body.squash
    body.scaleY = 1 / body.scaleX
  }

  // acceleration since the last tick, in the body's own rotated frame — captures
  // gravity, this tick's bounce, and any applyImpulse() called since last step()
  const ax = (body.vx - prevVx) / dt
  const ay = (body.vy - prevVy) / dt
  const cos = Math.cos(body.angle)
  const sin = Math.sin(body.angle)
  const localAx = ax * cos + ay * sin
  const localAy = -ax * sin + ay * cos

  for (const eye of body.eyes) {
    updateEye(eye, localAx, localAy, dt)
  }
}

export function step(bodies, dt = FIXED_DT) {
  for (const body of bodies) {
    stepBody(body, dt)
  }
}
