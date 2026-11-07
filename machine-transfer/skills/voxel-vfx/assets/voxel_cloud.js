// Reusable cube cloud. Needs THREE in scope. Add `export` when using it as a module.
// Skill VFX, built from real cubes. The voxel concept sheet is a shape reference only.
const ICE = [0x101a44, 0x20397a, 0x3e6cc0, 0x62aee8, 0x9ad9f7, 0xffffff].map((c) => new THREE.Color(c));
const cubeGeometry = new THREE.BoxGeometry(1, 1, 1);
const cM = new THREE.Matrix4(), cS = new THREE.Vector3(), cP = new THREE.Vector3(), cQ = new THREE.Quaternion();
function voxelCloud(items, glowLevel = 0.8) {
  const material = new THREE.MeshStandardMaterial({ roughness: 0.55, emissive: 0x16356e, emissiveIntensity: glowLevel });
  const mesh = new THREE.InstancedMesh(cubeGeometry, material, items.length);
  mesh.frustumCulled = false;
  items.forEach((item, n) => mesh.setColorAt(n, ICE[item.c]));
  const apply = (fn) => {
    items.forEach((item, n) => {
      cP.copy(item.p);
      const size = fn(item, cP);
      cM.compose(cP, cQ, cS.setScalar(Math.max(size, 0.0001)));
      mesh.setMatrixAt(n, cM);
    });
    mesh.instanceMatrix.needsUpdate = true;
  };
  return { mesh, apply };
}
const vox = (x, y, z, size, c, extra = {}) => ({ p: new THREE.Vector3(x, y, z), size, c, r: Math.random(), ...extra });
