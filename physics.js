export const CONFIG = {
  worldW: 160, worldH: 90,
  floorY: 78, wallLeft: 8, wallRight: 152,
  gravity: 420,
  floorRestitution: 0.55, wallRestitution: 0.60, botRestitution: 0.60,
  groundDampingLinear: 0.82, groundDampingAngular: 0.70,
  botRadius: 20,
  rotationQuantizeDeg: 15,
  pixelScale: 8,
  palette: ['#1a1a2e', '#e94560', '#0f3460', '#16213e', '#f5f5f5', '#ffd460', '#533483', '#0a0a0a'],
  outlineColor: '#0a0a0a',
  shadowColor: 'rgba(0,0,0,0.35)',
  eyeStiffness: 90,
  eyeDamping: 10,
  eyeAccelGain: 0.02,
  eyeClampRadius: 5.2,
  eyeSocketRadius: 6.0,
  pupilRadius: 3.4,
  eyeOffsetX: 8.0,
  eyeOffsetY: -7.0,
  squashCoefficient: 0.0025,
  squashMax: 0.6,
  squashDecayRate: 12,
  cameraShakeMax: 16,
  cameraShakeDecayRate: 10,
  speakLeadSeconds: 0.9,
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

// Simple circle-vs-circle rigid-body separation between bots — every body
// shares CONFIG.botRadius, so this is just pairwise distance-vs-2*radius,
// not a general collision solver. Positional push-apart + a restitution-based
// velocity bounce along the contact normal, same squash-on-impact treatment
// as floor/wall contact for visual consistency.
function resolveBotCollisions(bodies) {
  for (let i = 0; i < bodies.length; i++) {
    for (let j = i + 1; j < bodies.length; j++) {
      const a = bodies[i]
      const b = bodies[j]
      const dx = b.x - a.x
      const dy = b.y - a.y
      const dist = Math.hypot(dx, dy)
      const minDist = CONFIG.botRadius * 2
      if (dist <= 0 || dist >= minDist) continue

      const nx = dx / dist
      const ny = dy / dist
      const overlap = minDist - dist
      a.x -= (nx * overlap) / 2
      a.y -= (ny * overlap) / 2
      b.x += (nx * overlap) / 2
      b.y += (ny * overlap) / 2

      const relVx = b.vx - a.vx
      const relVy = b.vy - a.vy
      const closingSpeed = relVx * nx + relVy * ny
      if (closingSpeed < 0) {
        const impulse = (-(1 + CONFIG.botRestitution) * closingSpeed) / 2
        a.vx -= impulse * nx
        a.vy -= impulse * ny
        b.vx += impulse * nx
        b.vy += impulse * ny

        const impactSpeed = Math.abs(closingSpeed)
        const squash = Math.min(CONFIG.squashCoefficient * impactSpeed, CONFIG.squashMax)
        for (const body of [a, b]) {
          if (squash > body.squash) {
            body.squash = squash
            body.squashAxis = Math.abs(nx) > Math.abs(ny) ? 'x' : 'y'
          }
        }
      }
    }
  }
}

export function step(bodies, dt = FIXED_DT) {
  for (const body of bodies) {
    stepBody(body, dt)
  }
  resolveBotCollisions(bodies)
}
