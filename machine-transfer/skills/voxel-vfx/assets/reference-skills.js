// Reference only: uses the test page's player, enemies, fx, damage, shake, stop, and dimmer.
function frostCrescent() {
  const dir = facingDir(), start = player.position.clone().addScaledVector(dir, 0.6).setY(0.2);
  const cell = 0.3, items = [];
  for (let x = -4; x <= 4; x += cell) for (let z = -3.2; z <= 2.2; z += cell) {
    const outer = Math.hypot(x, z - 1), inner = Math.hypot(x, z - 2.3);
    if (outer > 3.9 || inner < 3.3) continue;
    const depth = Math.min((inner - 3.3) / 1.3, 1);      // 0 at the bright inner edge, 1 at the rough front
    const height = 1 + Math.round(Math.sin(Math.min(depth * 1.6, 1) * Math.PI) * 3 + Math.random());
    const c = depth < 0.22 ? 5 : depth < 0.42 ? 4 : depth < 0.65 ? 3 : depth < 0.85 ? 2 : 1;
    for (let h = 0; h < height; h++) items.push(vox(x, h * cell, z, cell * (0.82 + Math.random() * 0.22), c));
  }
  for (let n = 0; n < 34; n++) items.push(vox((Math.random() - 0.5) * 7, Math.random() * 1.3, 1 + Math.random() * 2.8, 0.09 + Math.random() * 0.14, 3 + (n % 3), { loose: true }));
  const cloud = voxelCloud(items);
  cloud.mesh.rotation.y = player.rotation.y;
  scene.add(cloud.mesh);
  const struck = new Set();
  let t = 0;
  fx.push((dt) => {
    t += dt;
    const k = t / 0.72, eased = 1 - (1 - Math.min(k, 1)) ** 2.2;
    cloud.mesh.position.copy(start).addScaledVector(dir, eased * 14);
    const grow = 0.6 + eased * 0.6;
    cloud.mesh.scale.set(grow, 1, grow);
    cloud.apply((item, p) => {
      if (item.loose) p.z += t * 3;
      const gone = (k - 0.5 - item.r * 0.42) / 0.12;     // crumbles cube by cube
      return item.size * Math.min(Math.min(t / 0.08, 1), 1 - Math.min(Math.max(gone, 0), 1));
    });
    for (const e of [...enemies]) {
      if (!struck.has(e) && e.g.position.distanceTo(cloud.mesh.position) < 3.2) { struck.add(e); damage(e, player.position, 12); shake = 0.14; }
    }
    if (k < 1) return true;
    scene.remove(cloud.mesh);
    return false;
  });
}

function blizzardVortex() {
  const centre = player.position.clone().addScaledVector(facingDir(), 3.2).setY(0);
  const items = [], levels = 12;
  // Funnel: uneven walls, thick where the two bands wind past.
  for (let l = 0; l < levels; l++) {
    const k = l / (levels - 1), radius = 0.32 + k ** 1.55 * 3.5, y = 0.2 + l * 0.25, size = 0.23 + k * 0.08;
    const count = Math.max(7, Math.round(radius * 2 * Math.PI / (size * 1.02)));
    for (let n = 0; n < count; n++) {
      const a = n / count * Math.PI * 2;
      const band = (Math.sin(a * 2 + l * 0.8) + 1) / 2;
      if (band < 0.2 && k > 0.15) continue;
      const c = band > 0.76 ? 5 : band > 0.52 ? 4 : band > 0.3 ? 3 : 2;
      const common = { a, speed: 5.4 - k * 3.2, phase: l * 0.5 };
      items.push(vox(0, y, 0, size, c, { ...common, radius }));
      if (band > 0.58) items.push(vox(0, y + size * 0.72, 0, size * 0.8, c, { ...common, radius: radius + size * 0.55 }));
    }
  }
  // Bright core running up the middle.
  for (let l = 0; l < 13; l++) for (let n = 0; n < 3; n++) {
    items.push(vox(0, 0.1 + l * 0.22, 0, 0.17, 5, { a: n * 2.1 + l * 0.45, radius: 0.13, speed: 9, phase: l }));
  }
  // Outer wind: broken arcs that tilt around the funnel.
  for (let ring = 0; ring < 3; ring++) {
    const radius = 4.1 + ring * 0.55, y = 0.7 + ring * 0.75;
    for (let n = 0; n < 76; n++) {
      if ((n + ring * 9) % 25 > 15) continue;
      items.push(vox(0, y, 0, 0.17, ring === 1 ? 4 : 3, { a: n / 76 * 6.283, radius, speed: 2.4 - ring * 0.5, wind: ring }));
    }
  }
  // Streams of cubes pulled inward along spiral paths.
  for (let chain = 0; chain < 5; chain++) for (let n = 0; n < 15; n++) {
    items.push(vox(0, 0, 0, 0.22 - n * 0.008, 4 + (n % 2), { stream: chain / 5 * 6.283, u: n / 15 * 0.34 }));
  }
  // Ground chunks kicked up around the base.
  for (let n = 0; n < 92; n++) {
    const a = Math.random() * 6.28, r = 1 + Math.random() * 3.6;
    items.push(vox(0, 0.06, 0, 0.13 + Math.random() * 0.24, 1 + n % 4, { a, radius: r, speed: 1.1, splash: n }));
  }
  const cloud = voxelCloud(items);
  cloud.mesh.position.copy(centre);
  scene.add(cloud.mesh);
  let t = 0, tick = 0.4;
  fx.push((dt) => {
    t += dt;
    const open = Math.min(t / 0.28, 1), close = Math.min(Math.max((2.8 - t) / 0.35, 0), 1);
    cloud.apply((item, p) => {
      if (item.stream !== undefined) {
        const u = (item.u + t * 0.52) % 1, r = 5.2 * (1 - u), a = item.stream + u * 8 - t * 2;
        p.set(Math.cos(a) * r, 0.5 + u * 2.4, Math.sin(a) * r);
        return item.size * open * close * Math.min(u * 8, 1);
      }
      const a = item.a - t * item.speed, r = item.radius * (0.35 + open * 0.65);
      p.x = Math.cos(a) * r; p.z = Math.sin(a) * r;
      if (item.wind !== undefined) p.y += Math.sin(a + item.wind * 2) * 0.55;
      else if (item.splash !== undefined) p.y += Math.abs(Math.sin(t * 7 + item.splash)) * 0.32;
      else p.y += Math.sin(t * 6 + item.phase) * 0.04;
      return item.size * open * close;
    });
    tick -= dt;
    for (const e of [...enemies]) {
      const to = centre.clone().sub(e.g.position).setY(0);
      if (to.length() < 5.2) {
        e.g.position.addScaledVector(to.normalize(), dt * 4);
        if (tick <= 0) damage(e, centre, 0);
      }
    }
    if (tick <= 0) tick = 0.55;
    if (t < 2.8) return true;
    scene.remove(cloud.mesh);
    return false;
  });
}

function winterEclipse() {
  const IMPACT = 1.4, END = 2.7;
  const centre = player.position.clone().addScaledVector(facingDir(), 3).setY(0);
  const root = new THREE.Group();
  root.position.copy(centre);
  scene.add(root);

  // Crater: a dark floor inside a raised stepped wall, so it reads as a deep hole.
  const crater = [];
  for (let x = -5.6; x <= 5.6; x += 0.4) for (let z = -5.6; z <= 5.6; z += 0.4) {
    const r = Math.hypot(x, z);
    if (r > 5.6) continue;
    const wall = Math.max(0, Math.round((r - 3.5) * 2.2 * (1.1 - Math.max(r - 4.8, 0))));
    for (let h = 0; h <= wall; h++) {
      const c = r < 3.1 ? 0 : h === wall ? (r > 4.6 ? 3 : 2) : 1;
      crater.push(vox(x, 0.05 + h * 0.3, z, 0.39, c, { d: r, h }));
    }
  }

  // Spikes: clusters of narrowing stacks with uneven height and lean.
  const rim = [];
  for (let n = 0; n < 15; n++) {
    const base = n / 15 * Math.PI * 2 + Math.random() * 0.22;
    for (let m = 0; m < 3; m++) {
      const a = base + (m - 1) * 0.09, r = 5 + Math.random() * 0.9;
      const tall = (m === 1 ? 11 : 5) + Math.floor(Math.random() * 6), lean = 0.06 + Math.random() * 0.13;
      for (let h = 0; h < tall; h++) {
        const k = h / tall, w = 0.68 * (1 - k) ** 1.15 + 0.06, off = h * lean;
        rim.push(vox(Math.cos(a) * (r + off), 0.15 + h * 0.3, Math.sin(a) * (r + off), w, k > 0.72 ? 5 : k > 0.42 ? 4 : 3, { delay: k * 0.12 + m * 0.02 }));
      }
    }
  }
  // Raised wave of blocks and flying chips.
  for (let n = 0; n < 90; n++) {
    const a = n / 90 * 6.283;
    rim.push(vox(0, 0.2, 0, 0.42, 3 + n % 2, { waveA: a }));
  }
  for (let n = 0; n < 80; n++) {
    const a = Math.random() * 6.28, v = 4 + Math.random() * 9;
    rim.push(vox(Math.cos(a) * 5, 0.1, Math.sin(a) * 5, 0.12 + Math.random() * 0.26, 3 + n % 3, { fly: new THREE.Vector3(Math.cos(a) * v, 1 + Math.random() * 4, Math.sin(a) * v) }));
  }
  // Light burst: straight lines of cubes that shoot outward at impact.
  for (let line = 0; line < 14; line++) for (let n = 0; n < 12; n++) {
    rim.push(vox(0, 0.9, 0, 0.3 - n * 0.016, 5, { ray: line / 14 * 6.283, n }));
  }

  // Moon: a cube shell split into plates, with wide dark cracks.
  const seeds = Array.from({ length: 13 }, () => new THREE.Vector3().randomDirection());
  const plates = seeds.map((seed) => seed.clone().multiplyScalar(5 + Math.random() * 5).setY(seed.y * 6 + 3));
  const moonItems = [], R = 2.1, cell = 0.28;
  for (let x = -R; x <= R; x += cell) for (let y = -R; y <= R; y += cell) for (let z = -R; z <= R; z += cell) {
    const len = Math.hypot(x, y, z);
    if (len > R || len < R - cell * 1.5) continue;
    const u = new THREE.Vector3(x, y, z).normalize();
    const near = seeds.map((seed, n) => [seed.distanceTo(u), n]).sort((p, q) => p[0] - q[0]);
    const crack = near[1][0] - near[0][0] < 0.14;
    moonItems.push(vox(x, y, z, cell * 0.96, crack ? 0 : [3, 4, 3, 2, 4][near[0][1] % 5], { plate: near[0][1], crack }));
  }
  // Eclipse halo: a broken ring of bright cubes circling the moon.
  const halo = [];
  for (let n = 0; n < 72; n++) if (n % 12 < 9) halo.push(vox(0, 0, 0, 0.2, n % 3 ? 5 : 4, { a: n / 72 * 6.283 }));

  const floor = voxelCloud(crater, 0.12), spikes = voxelCloud(rim), moon = voxelCloud(moonItems, 0.5), ring = voxelCloud(halo, 1.4);
  root.add(floor.mesh, spikes.mesh, moon.mesh, ring.mesh);
  let t = 0, landed = false, age = 0;
  fx.push((dt) => {
    t += dt;
    const dark = t < IMPACT ? Math.min(t / 0.45, 1) * 0.72 : 0;
    if (t < IMPACT) { dimmer.style.background = '#02040e'; dimmer.style.opacity = dark; }
    else { dimmer.style.background = '#bfe8ff'; dimmer.style.opacity = Math.max(0, 0.55 * (1 - (t - IMPACT) / 0.22)); }
    const out = t > END - 0.5 ? Math.max(0, (END - t) / 0.5) : 1;
    floor.apply((item) => item.size * Math.min(Math.max((t / 0.55) * 7 - item.d, 0), 1) * out);
    const y = 8.6 - Math.min(t / IMPACT, 1) ** 3.2 * 6.5;
    if (!landed) {
      moon.mesh.position.y = y;
      moon.mesh.rotation.y += dt * 1.2;
      moon.apply((item) => item.size * Math.min(t / 0.2, 1));
      ring.mesh.position.y = y;
      ring.apply((item, p) => {
        const a = item.a + t * 3;
        p.set(Math.cos(a) * 3.1, Math.sin(a * 2) * 0.2, Math.sin(a) * 3.1);
        return item.size * Math.min(t / 0.35, 1);
      });
      spikes.apply(() => 0);
    }
    if (t >= IMPACT && !landed) {
      landed = true;
      ring.mesh.visible = false;
      stop = 0.13; shake = 0.6;
      for (const e of [...enemies]) if (e.g.position.distanceTo(centre) < 6.5) { damage(e, centre, 16); if (enemies.includes(e)) damage(e, centre, 16); }
    }
    if (landed) {
      age += dt;
      moon.apply((item, p) => {
        p.addScaledVector(plates[item.plate], age);          // plates fly apart whole
        p.y -= 9 * age * age;
        return item.size * Math.max(0, 1 - age / 0.8);
      });
      spikes.apply((item, p) => {
        if (item.fly) {
          p.addScaledVector(item.fly, age);
          p.y = Math.max(0.05, p.y - 8 * age * age);
          return item.size * Math.max(0, 1 - age / 0.9);
        }
        if (item.waveA !== undefined) {
          const r = 1 + age * 11;
          p.set(Math.cos(item.waveA) * r, 0.2 + Math.sin(Math.min(age * 4, 1) * Math.PI) * 0.9, Math.sin(item.waveA) * r);
          return item.size * Math.max(0, 1 - age / 0.6);
        }
        if (item.ray !== undefined) {
          const r = 1 + item.n * 0.65 + age * 15;
          p.set(Math.cos(item.ray) * r, 0.9, Math.sin(item.ray) * r);
          return item.size * Math.max(0, 1 - age / 0.38);
        }
        return item.size * Math.min(Math.max((age - item.delay) / 0.09, 0), 1) * out;
      });
    }
    if (t < END) return true;
    scene.remove(root);
    dimmer.style.opacity = 0;
    return false;
  });
}

function castSkill(n) {
  const skill = { 1: [frostCrescent, 1.4, 0], 2: [blizzardVortex, 7, 2], 3: [winterEclipse, 14, 2] }[n];
  if (!skill || !ready || over || cooldown[n] > 0) return;
  cooldown[n] = skill[1];
  startStep(skill[2]);
  skill[0]();
}

function runFx(dt) {
  for (const n of [1, 2, 3]) cooldown[n] = Math.max(0, cooldown[n] - dt);
  for (let i = fx.length - 1; i >= 0; i--) if (!fx[i](dt)) fx.splice(i, 1);
}

