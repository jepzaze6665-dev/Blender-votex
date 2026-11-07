// Loads the floating ice temple built in Blender: voxel-map/build_map.py exports the model and
// walk data. Sky, shadows, snow, and gentle motion are added here, since a GLB does not carry them.
import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';

const key = (x, z) => `${Math.round(x)},${Math.round(z)}`;

function addSky(scene) {
  const dome = new THREE.Mesh(new THREE.SphereGeometry(280, 32, 18), new THREE.ShaderMaterial({
    side: THREE.BackSide, depthWrite: false, fog: false,
    vertexShader: 'varying vec3 p; void main(){ p = normalize(position); gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0); }',
    fragmentShader: `varying vec3 p;
      void main(){
        vec3 low = vec3(0.34, 0.45, 0.82), mid = vec3(0.07, 0.11, 0.42), high = vec3(0.012, 0.022, 0.13);
        float h = clamp(p.y * 0.5 + 0.5, 0.0, 1.0);
        vec3 c = mix(low, mid, smoothstep(0.32, 0.56, h));
        gl_FragColor = vec4(mix(c, high, smoothstep(0.55, 0.9, h)), 1.0);
      }`,
  }));
  scene.add(dome);
  const stars = new Float32Array(1400 * 3);
  for (let i = 0; i < 1400; i++) {
    const v = new THREE.Vector3().randomDirection().multiplyScalar(270);
    v.y = Math.abs(v.y) + 10;
    stars.set([v.x, v.y, v.z], i * 3);
  }
  const g = new THREE.BufferGeometry().setAttribute('position', new THREE.BufferAttribute(stars, 3));
  scene.add(new THREE.Points(g, new THREE.PointsMaterial({ color: 0xdcecff, size: 1, sizeAttenuation: false, fog: false, transparent: true, opacity: 0.8 })));
}

export async function loadIceMap(scene, renderer) {
  const stamp = Date.now();   // never reuse a cached map
  const [gltf, data] = await Promise.all([
    new GLTFLoader().loadAsync(`assets/ice_temple_map.glb?t=${stamp}`),
    fetch(`assets/ice_temple_collision.json?t=${stamp}`).then((r) => r.json()),
  ]);
  scene.add(gltf.scene);
  scene.traverse((o) => {
    if (!o.isLight) return;
    o.intensity *= o.isDirectionalLight ? 0.62 : 0.5;
    if (o.isDirectionalLight) {
      o.position.set(-34, 70, 26);
      o.castShadow = true;
      o.shadow.mapSize.set(4096, 4096);
      Object.assign(o.shadow.camera, { left: -72, right: 72, top: 72, bottom: -72, far: 170 });
      o.shadow.bias = -0.0006;
    }
  });
  renderer.shadowMap.enabled = true;
  renderer.shadowMap.type = THREE.PCFSoftShadowMap;
  gltf.scene.traverse((o) => {
    if (!o.isMesh) return;
    o.castShadow = o.name !== 'Clouds';
    o.receiveShadow = true;
    o.frustumCulled = false;
  });
  addSky(scene);
  scene.background = null;
  scene.fog = new THREE.Fog(0x314ba4, 75, 235);

  for (const [x, y, z, power] of [[-7, 22, -44, 650], [0, 6, 2, 260], [34, 14, -19, 220]]) {
    const l = new THREE.PointLight(0x62c8ff, power, 42, 1.6);
    l.position.set(x, y, z);
    scene.add(l);
  }

  // Snow: a box of flakes that wraps around the player.
  const count = 1200, flakes = new Float32Array(count * 3), span = 64;
  for (let i = 0; i < count * 3; i++) flakes[i] = (Math.random() - 0.5) * span;
  const snowGeometry = new THREE.BufferGeometry().setAttribute('position', new THREE.BufferAttribute(flakes, 3));
  const snow = new THREE.Points(snowGeometry, new THREE.PointsMaterial({ color: 0xeaf5ff, size: 0.13, transparent: true, opacity: 0.85 }));
  snow.frustumCulled = false;
  scene.add(snow);

  const find = (n) => gltf.scene.getObjectByName(n);
  const clouds = find('Clouds'), floating = find('Floating'), crystals = find('Crystals');
  const crystalMaterial = crystals?.material;
  let time = 0;

  const groundAt = (x, z) => data.cells[key(x, z)] ?? null;
  const canStand = (x, z, fromY) => {
    const h = groundAt(x, z);
    return h !== null && h - fromY < 1.3 && !data.blockers.some((b) => Math.hypot(x - b.x, z - b.z) < b.r);
  };
  function update(dt, player) {
    time += dt;
    if (clouds) clouds.position.x = Math.sin(time * 0.05) * 8;
    if (floating) floating.position.y = Math.sin(time * 0.75) * 0.35;
    if (crystalMaterial) crystalMaterial.emissiveIntensity = 1 + Math.sin(time * 1.7) * 0.22;
    const p = snowGeometry.attributes.position;
    for (let i = 0; i < count; i++) {
      let y = p.getY(i) - dt * (1.2 + (i % 5) * 0.25);
      if (y < -span / 2) y += span;
      p.setY(i, y);
      p.setX(i, p.getX(i) + Math.sin(time + i) * dt * 0.25);
    }
    p.needsUpdate = true;
    snow.position.set(player.x, player.y + 8, player.z);
  }
  return { groundAt, canStand, update, spawn: new THREE.Vector3(...data.spawn), arena: data.arena };
}
