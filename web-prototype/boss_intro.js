// Boss intro for the test page: the dragon wakes from its ice prison.
// Mock only. Combat and AI belong in the game project.
import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';

const LENGTH = 7, BURST = 3, ROAR = 4, TITLE = 5.7, RETURN = 6.2;
const NAME = 'HRIMVAEL', SUBTITLE = 'ผู้เฝ้าธารน้ำแข็ง';
// Shots: start time, then camera and look-at offsets at the shot's start and end, from the dragon.
// The dragon faces +Z.
const SHOTS = [
  [0, 1.5, [-15, 5, 30], [-10, 5, 25], [0, 6, 2], [0, 6, 2]],
  [1.5, 3, [-5, 4, 19], [5, 5, 18], [0, 5.5, 5], [0, 6, 5]],
  [3, 4, [0, 5, 22], [0, 7, 33], [0, 7, 3], [0, 8, 2]],
  [4, 5.7, [-17, 3, 36], [-12, 3, 32], [0, 10, 3], [0, 11, 3]],
  [5.7, 7, [-12, 3, 32], [-11, 3, 31], [0, 11, 3], [0, 11, 3]],
];
const ease = (t) => t * t * (3 - 2 * t);
const SLOW_FROM = 3.02, SLOW_TO = 3.11, SLOW = 0.22;      // about 0.4 real seconds as the ice bursts
const EYES_OPEN = 2.25;                                   // the eyes light in the dark, just before the burst
const DARK = 0.2;                                         // light left in the world just before the burst

function overlay() {
  const flash = document.createElement('div');
  flash.style.cssText = 'position:fixed;inset:0;background:#dff4ff;opacity:0;pointer-events:none;z-index:20';
  const dark = document.createElement('div');
  dark.style.cssText = 'position:fixed;inset:0;background:#0a1230;mix-blend-mode:multiply;opacity:0;pointer-events:none;z-index:19';
  const title = document.createElement('div');
  title.style.cssText = 'position:fixed;left:0;right:0;bottom:14%;text-align:center;color:#eaf8ff;opacity:0;pointer-events:none;z-index:21;font-family:sans-serif;text-shadow:0 0 18px #2f9dff,0 2px 4px #000';
  title.innerHTML = `<div style="font-size:clamp(34px,7vw,76px);font-weight:800;letter-spacing:.22em">${NAME}</div><div style="font-size:clamp(15px,2.4vw,24px);margin-top:6px">${SUBTITLE}</div>`;
  document.body.append(dark, flash, title);
  return { dark, flash, title };
}

export function createBoss(scene, arena, effects) {
  const root = new THREE.Group();
  root.position.set(arena.x, arena.top, arena.z - 3);
  root.rotation.y = Math.PI;
  root.visible = false;
  scene.add(root);
  const ui = overlay();
  const boss = { ready: false, playing: false, seen: false, time: 0, root, shake: 0 };
  let mixer, intro, idle, iceMixer, ice, iceAction, head, core = [], eyes = [], iceMaterials = [], burst = false, roared = false;

  // A ring of voxel frost that runs across the arena on the roar.
  const RING = 72;
  const ring = new THREE.InstancedMesh(new THREE.BoxGeometry(0.7, 0.5, 0.7),
    new THREE.MeshStandardMaterial({ color: 0xbfeaff, emissive: 0x4fb4ff, emissiveIntensity: 1.2 }), RING);
  ring.visible = false;
  ring.frustumCulled = false;
  scene.add(ring);
  const dummy = new THREE.Object3D();
  let ringTime = -1;

  // Snow that winds up around the dragon from the roar.
  const SNOW = 280;
  const snow = new THREE.InstancedMesh(new THREE.BoxGeometry(1, 1, 1),
    new THREE.MeshStandardMaterial({ color: 0xdff4ff, emissive: 0x7cc8ff, emissiveIntensity: 0.7 }), SNOW);
  snow.visible = false;
  snow.frustumCulled = false;
  scene.add(snow);
  const flakes = Array.from({ length: SNOW }, () => ({ a: Math.random() * Math.PI * 2, r: 7 + Math.random() * 7, delay: Math.random() * 1.1, size: 0.14 + Math.random() * 0.3, rise: 6 + Math.random() * 7 }));

  // Light levels to dim; read once, so every play starts from the map's own values.
  const lights = [];
  scene.traverse((o) => { if (o.isLight) lights.push([o, o.intensity]); });
  const sky = scene.background?.isColor ? scene.background.clone() : null;
  function setLight(level) {
    for (const [light, base] of lights) light.intensity = base * level;
    if (sky) scene.background.copy(sky).multiplyScalar(level);
    ui.dark.style.opacity = Math.max(0, 1 - level) * 0.7;
  }
  const crack = { uCore: { value: new THREE.Vector3() }, uReach: { value: 0 } };
  let pillars = [];

  const loader = new GLTFLoader();
  const stamp = Date.now();
  loader.load(`assets/voxel_dragon_rigged.glb?t=${stamp}`, (gltf) => {
    root.add(gltf.scene);
    mixer = new THREE.AnimationMixer(gltf.scene);
    const clip = (n) => gltf.animations.find((a) => a.name === n);
    head = gltf.scene.getObjectByName('Head');
    intro = mixer.clipAction(clip('Intro'));
    intro.setLoop(THREE.LoopOnce);
    intro.clampWhenFinished = true;
    idle = mixer.clipAction(clip('Idle'));
    gltf.scene.traverse((o) => {
      if (!o.isMesh) return;
      for (const m of [o.material].flat()) {
        if (m.name === 'M_Dragon7' && !core.includes(m)) core.push(m);
        if (m.name === 'M_Dragon8' && !eyes.includes(m)) eyes.push(m);
      }
    });
    loader.load(`assets/voxel_dragon_ice.glb?t=${stamp}`, (iceGltf) => {
      ice = iceGltf.scene;
      root.add(ice);
      iceMixer = new THREE.AnimationMixer(ice);
      iceAction = iceMixer.clipAction(new THREE.AnimationClip('Break', -1, iceGltf.animations.flatMap((a) => a.tracks)));
      iceAction.setLoop(THREE.LoopOnce);
      iceAction.clampWhenFinished = true;
      ice.traverse((o) => {
        if (!o.isMesh) return;
        for (const m of [o.material].flat()) {
          m.transparent = true;
          if (m.name === 'M_IceCrack') {
            m.onBeforeCompile = (shader) => {
              Object.assign(shader.uniforms, crack);
              shader.vertexShader = 'varying vec3 vIcePos;\n' + shader.vertexShader.replace('#include <begin_vertex>',
                '#include <begin_vertex>\nvIcePos = (modelMatrix * vec4(transformed, 1.0)).xyz;');
              shader.fragmentShader = 'uniform vec3 uCore; uniform float uReach; varying vec3 vIcePos;\n' +
                shader.fragmentShader.replace('#include <emissivemap_fragment>',
                  '#include <emissivemap_fragment>\n totalEmissiveRadiance *= step(distance(vIcePos, uCore), uReach);');
            };
          }
          m.depthWrite = false;
          if (!iceMaterials.includes(m)) { iceMaterials.push(m); m.userData.glow = m.emissiveIntensity; }
        }
      });
      loader.load(`assets/voxel_dragon_pillars.glb?t=${stamp}`, (pillarGltf) => {
        pillarGltf.scene.position.set(arena.x, arena.top, arena.z);
        scene.add(pillarGltf.scene);
        pillarGltf.scene.traverse((o) => { if (/^Pillar\d+$/.test(o.name)) pillars.push(o); });
        boss.reset();
        boss.ready = true;
      });
    });
  });

  boss.reset = () => {
    boss.playing = false;
    boss.time = 0;
    burst = roared = false;
    root.visible = true;
    ice.visible = true;
    idle.stop();
    intro.reset().play();
    intro.paused = true;
    iceAction.reset().play();
    iceAction.paused = true;
    mixer.update(0);
    iceMixer.update(0);
    ui.flash.style.opacity = 0;
    ui.title.style.opacity = 0;
    crack.uReach.value = 0;
    setLight(1);
    for (const m of eyes) m.emissiveIntensity = 0;
    snow.visible = false;
    for (const p of pillars) { p.scale.set(1, 0.001, 1); p.visible = false; p.userData.popped = false; }
  };
  boss.start = () => {
    if (!boss.ready) return;
    boss.reset();
    boss.playing = boss.seen = true;
    for (const e of effects.enemies) e.g.visible = false;
    intro.paused = iceAction.paused = false;
  };

  function burstEffects() {
    const c = root.position;
    for (let n = 0; n < 70; n++) {
      const a = Math.random() * Math.PI * 2, up = Math.random();
      effects.spawn(new THREE.Vector3(c.x + Math.cos(a) * 5, c.y + 2 + up * 7, c.z + Math.sin(a) * 6),
        new THREE.Vector3(Math.cos(a) * (6 + up * 9), 4 + up * 9, Math.sin(a) * (6 + up * 9)), 1.3, 0.1 + Math.random() * 0.16);
    }
  }
  function updateRing(dt) {
    if (ringTime < 0) return;
    ringTime += dt;
    const t = ringTime / 1.1;
    if (t >= 1) { ringTime = -1; ring.visible = false; return; }
    const radius = 3 + ease(t) * 15;
    for (let n = 0; n < RING; n++) {
      const a = n / RING * Math.PI * 2;
      dummy.position.set(arena.x + Math.cos(a) * radius, arena.top + 0.25 + (n % 3) * 0.14, arena.z + Math.sin(a) * radius);
      dummy.scale.setScalar(1.3 * (1 - t) + 0.05);
      dummy.rotation.y = a;
      dummy.updateMatrix();
      ring.setMatrixAt(n, dummy.matrix);
    }
    ring.instanceMatrix.needsUpdate = true;
  }

  function updatePillars(t) {
    pillars.forEach((p, n) => {
      const k = (t - ROAR - 0.1 - (n % 6) * 0.05) / 0.42;
      if (k <= 0) return;
      p.visible = true;
      // A fast rise that overshoots, then settles.
      const grow = k >= 1 ? 1 : 1 - Math.pow(1 - k, 3) + Math.sin(k * Math.PI) * 0.12;
      p.scale.set(1, Math.max(0.001, grow), 1);
      if (!p.userData.popped) {
        p.userData.popped = true;
        const at = p.getWorldPosition(new THREE.Vector3());
        for (let i = 0; i < 7; i++) effects.spawn(at.clone(), new THREE.Vector3((Math.random() - 0.5) * 7, 5 + Math.random() * 6, (Math.random() - 0.5) * 7), 0.9, 0.12 + Math.random() * 0.14);
      }
    });
  }
  function updateSnow(t) {
    const life = t - 3.9;
    snow.visible = life > 0 && t < LENGTH + 0.2;
    if (!snow.visible) return;
    const c = root.position;
    flakes.forEach((f, n) => {
      const k = THREE.MathUtils.clamp((life - f.delay) / 2.3, 0, 1);
      const a = f.a + life * 2.4 + k * 2.6;
      const r = f.r * (1 - k * 0.3);
      dummy.position.set(c.x + Math.cos(a) * r, c.y + 0.5 + k * f.rise * 2.2, c.z + 3 + Math.sin(a) * r);
      dummy.rotation.set(a, a * 1.3, 0);
      dummy.scale.setScalar(k > 0 && k < 1 ? f.size * Math.sin(k * Math.PI) * 1.6 : 0.001);
      dummy.updateMatrix();
      snow.setMatrixAt(n, dummy.matrix);
    });
    snow.instanceMatrix.needsUpdate = true;
  }

  boss.update = (realDt) => {
    if (!boss.ready) return;
    const slow = boss.playing && boss.time >= SLOW_FROM && boss.time < SLOW_TO;
    const dt = slow ? realDt * SLOW : realDt;
    mixer.update(dt);
    updateRing(dt);
    if (!boss.playing) {
      const beat = 1 + Math.sin(performance.now() * 0.002) * 0.25;
      for (const m of core) m.emissiveIntensity = beat * 0.5;
      return;
    }
    iceMixer.update(dt);
    boss.time += dt;
    const t = boss.time;
    updatePillars(t);
    updateSnow(t);
    // The world dims toward the burst, then the light comes back past normal.
    setLight(t < BURST ? 1 - (1 - DARK) * ease(Math.min(1, t / 2.8)) : 1 + Math.max(0, 0.5 * (1 - (t - BURST) / 0.8)));
    core[0] && root.getObjectByName('Core').getWorldPosition(crack.uCore.value);
    crack.uReach.value = t < 1.3 ? 0 : (t - 1.3) * 11;
    const open = THREE.MathUtils.clamp((t - EYES_OPEN) / 0.22, 0, 1);
    for (const m of eyes) m.emissiveIntensity = t < BURST ? open * (9 + Math.sin(t * 14)) : 4;
    // The core beats faster until the ice gives way.
    const speed = t < BURST ? 2 + t * 3.2 : 3;
    for (const m of core) m.emissiveIntensity = 0.5 + (0.5 + 0.5 * Math.sin(t * speed * 2)) * (t < BURST ? 0.4 + t * 0.35 : 0.8);
    for (const m of iceMaterials) m.emissiveIntensity = m.userData.glow * (1 + Math.max(0, t - 1.5) * 0.8);
    boss.shake = t < 1.5 ? 0 : t < BURST ? 0.1 + (t - 1.5) * 0.14 : t < BURST + 0.5 ? 0.7 : t > ROAR && t < TITLE ? 0.45 : 0;
    if (!burst && t >= BURST) { burst = true; burstEffects(); }
    if (!roared && t >= ROAR) { roared = true; ringTime = 0; ring.visible = true; }
    ui.flash.style.opacity = t >= BURST ? Math.max(0, 0.85 * (1 - (t - BURST) / 0.22)) : 0;
    ui.title.style.opacity = t < TITLE ? 0 : t < LENGTH - 0.3 ? Math.min(1, (t - TITLE) / 0.3) : Math.max(0, (LENGTH - t) / 0.3);
    if (t >= 5.2) ice.visible = false;
    if (t >= LENGTH) {
      boss.playing = false;
      boss.shake = 0;
      setLight(1);
      for (const e of effects.enemies) e.g.visible = true;
      ui.title.style.opacity = 0;
      idle.reset().play();
      intro.crossFadeTo(idle, 0.4, false);
    }
  };

  const faceAt = new THREE.Vector3();
  const from = new THREE.Vector3(), to = new THREE.Vector3(), lookAt = new THREE.Vector3();
  const home = new THREE.Vector3(), homeTurn = new THREE.Quaternion();
  const offset = (a, b, k, out) => out.set(a[0] + (b[0] - a[0]) * k, a[1] + (b[1] - a[1]) * k, a[2] + (b[2] - a[2]) * k).add(root.position);
  // Call after the normal camera is placed: it takes over, then hands back near the end.
  boss.applyCamera = (camera) => {
    if (!boss.playing) return;
    home.copy(camera.position);
    homeTurn.copy(camera.quaternion);
    const t = boss.time;
    const shot = SHOTS.find((s) => t < s[1]) || SHOTS[SHOTS.length - 1];
    const k = ease(Math.min(1, (t - shot[0]) / (shot[1] - shot[0])));
    offset(shot[2], shot[3], k, to);
    offset(shot[4], shot[5], k, lookAt);
    camera.position.copy(to);
    camera.lookAt(lookAt);
    if (t >= EYES_OPEN && t < BURST) {
      // Cut to the face as the eyes open, creeping closer.
      head.getWorldPosition(faceAt);
      const k = (t - EYES_OPEN) / (BURST - EYES_OPEN);
      camera.position.set(faceAt.x - 1.4, faceAt.y + 0.6, faceAt.z + 8.5 - k * 1.6);
      camera.lookAt(faceAt.x, faceAt.y, faceAt.z + 2.5);
    }
    const back = ease(THREE.MathUtils.clamp((t - RETURN) / (LENGTH - RETURN), 0, 1));
    if (back > 0) {
      from.copy(camera.position);
      camera.position.lerpVectors(from, home, back);
      camera.quaternion.slerp(homeTurn, back);
    }
    camera.position.x += (Math.random() - 0.5) * boss.shake;
    camera.position.y += (Math.random() - 0.5) * boss.shake;
  };
  return boss;
}
