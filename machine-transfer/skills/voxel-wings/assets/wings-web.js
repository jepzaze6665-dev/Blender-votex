// Excerpt from the test page. Needs THREE, GLTFLoader, player, velocity, airborne, attack, and spawn().
// Call loadWings(bodyBone) at rest, and updateWings(dt, moving) each frame.
// Crystal wings from Blender (voxel-wings/build_wings.py). Press T to change tier.
let wings = null;
const WING_TIERS = [[/Frame|Primary/, 1], [/Secondary|Core|Gem/, 2], [/Covert|Shard/, 3]];
const PULSE_POWER = [0, 0, 0.45, 0.8, 1.25];
const WING_IDLE_FOLD = 0.6;   // 1 is fully folded, 0 fully open
function setWingTier(tier) {
  wings.tier = tier;
  wings.model.traverse((o) => {
    for (const [pattern, need] of WING_TIERS) if (pattern.test(o.name)) o.visible = tier >= need;
  });
}
function loadWings(bone) {
  // Measured at rest, before clips start: wings are built in the character's model space.
  const fromBone = bone.matrixWorld.clone().invert().multiply(player.matrixWorld);
  const wingFile = new URLSearchParams(location.search).get('wing') === 'slim' ? 'voxel_wings_slim' : 'voxel_wings';
  new GLTFLoader().load(`assets/${wingFile}.glb?t=${Date.now()}`, (gltf) => {
    const seat = new THREE.Group();
    seat.applyMatrix4(fromBone);
    // Scale around the point where the wings meet the back, so they stay attached.
    const WING_SCALE = 0.62;
    gltf.scene.scale.setScalar(WING_SCALE);
    gltf.scene.position.set(0, 0.98 * (1 - WING_SCALE), 0.42 * (1 - WING_SCALE));
    seat.add(gltf.scene);
    bone.add(seat);
    const mixer = new THREE.AnimationMixer(gltf.scene);
    mixer.clipAction(new THREE.AnimationClip('Wings', -1, gltf.animations.flatMap((a) => a.tracks))).play();
    const tips = [];
    gltf.scene.traverse((o) => { if (/^Tip[RL]/.test(o.name)) tips.push(o); });
    // Pulse: a band of light runs out from the core through every feather.
    const pulse = { uHead: { value: 0 }, uCenter: { value: new THREE.Vector3() }, uPower: { value: 0 } };
    const seen = new Set();
    gltf.scene.traverse((o) => {
      if (!o.isMesh) return;
      for (const m of [o.material].flat()) {
        if (seen.has(m)) continue;
        seen.add(m);
        m.onBeforeCompile = (shader) => {
          Object.assign(shader.uniforms, pulse);
          shader.vertexShader = 'varying vec3 vWingPos;\n' + shader.vertexShader.replace('#include <begin_vertex>',
            '#include <begin_vertex>\nvWingPos = (modelMatrix * vec4(transformed, 1.0)).xyz;');
          shader.fragmentShader = 'uniform float uHead; uniform float uPower; uniform vec3 uCenter; varying vec3 vWingPos;\n' +
            shader.fragmentShader.replace('#include <emissivemap_fragment>', `#include <emissivemap_fragment>
              float wingBand = (distance(vWingPos, uCenter) - uHead) / 0.34;
              totalEmissiveRadiance += diffuseColor.rgb * uPower * exp(-wingBand * wingBand);`);
        };
        m.needsUpdate = true;
      }
    });
    wings = { model: gltf.scene, mixer, tips, tier: 4, spark: 0, pulse, fold: 1, time: 0,
      core: gltf.scene.getObjectByName('Core'), foldR: gltf.scene.getObjectByName('FoldR'), foldL: gltf.scene.getObjectByName('FoldL') };
    setWingTier(4);
  });
}
function updateWings(dt, moving) {
  wings.mixer.update(dt * (moving ? 2.1 : 1));
  wings.time += dt;
  // Folded against the back at rest; open when moving, jumping, or attacking.
  const open = moving || airborne || attack >= 0;
  wings.fold += ((open ? 0 : WING_IDLE_FOLD) - wings.fold) * (1 - Math.exp(-(open ? 11 : 5) * dt));
  for (const [node, side] of [[wings.foldR, 1], [wings.foldL, -1]]) {
    node.rotation.set(0, -side * 1.18 * wings.fold, -side * 0.34 * wings.fold);
    node.scale.setScalar(1 - wings.fold * 0.2);
  }
  const { pulse } = wings;
  wings.core.getWorldPosition(pulse.uCenter.value);
  pulse.uHead.value = (wings.time % 2.2) / 2.2 * 2.4 - 0.2;
  pulse.uPower.value = PULSE_POWER[wings.tier];
  if (wings.tier < 3 || wings.fold > 0.5) return;
  wings.spark -= dt;
  if (wings.spark > 0) return;
  wings.spark = wings.tier === 4 ? 0.018 : 0.06;
  // Sparkles flow off the feather tips and trail behind the character.
  const at = wings.tips[Math.floor(Math.random() * wings.tips.length)].getWorldPosition(new THREE.Vector3());
  const drift = velocity.clone().multiplyScalar(-0.42);
  drift.y = -0.5 - Math.random() * 0.45;
  drift.x += (Math.random() - 0.5) * 0.3; drift.z += (Math.random() - 0.5) * 0.3;
  spawn(at, drift, 0.85, 0.035 + Math.random() * 0.05);
}

