(() => {
  const container = document.getElementById('viewport');
  if (!window.THREE || !window.EMBEDDED_STL) {
    container.textContent = 'Не удалось запустить 3D-просмотр. Используйте ссылки на STL.';
    return;
  }

  const scene = new THREE.Scene();
  scene.background = new THREE.Color(0xe9edef);
  scene.fog = new THREE.Fog(0xe9edef, 190, 330);

  const camera = new THREE.PerspectiveCamera(34, 1, 0.1, 600);
  camera.up.set(0, 0, 1);
  const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: false });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
  renderer.outputEncoding = THREE.sRGBEncoding;
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = 0.88;
  renderer.shadowMap.enabled = true;
  renderer.shadowMap.type = THREE.PCFSoftShadowMap;
  container.appendChild(renderer.domElement);

  const controls = new THREE.OrbitControls(camera, renderer.domElement);
  controls.enableDamping = true;
  controls.dampingFactor = 0.075;
  controls.minDistance = 55;
  controls.maxDistance = 240;
  controls.maxPolarAngle = Math.PI * 0.91;
  controls.autoRotateSpeed = 0.8;

  scene.add(new THREE.HemisphereLight(0xf8fbff, 0x6f7674, 0.65));
  const key = new THREE.DirectionalLight(0xffffff, 0.9);
  key.position.set(-55, -60, 110);
  key.castShadow = true;
  key.shadow.mapSize.set(2048, 2048);
  key.shadow.camera.left = -85;
  key.shadow.camera.right = 85;
  key.shadow.camera.top = 85;
  key.shadow.camera.bottom = -85;
  key.shadow.camera.near = 10;
  key.shadow.camera.far = 240;
  key.shadow.bias = -0.0004;
  scene.add(key);
  const fill = new THREE.DirectionalLight(0xc8deed, 0.45);
  fill.position.set(80, 50, 45);
  scene.add(fill);

  const ground = new THREE.Mesh(
    new THREE.PlaneGeometry(320, 320),
    new THREE.ShadowMaterial({ color: 0x34424b, opacity: 0.17 })
  );
  ground.position.z = -0.12;
  ground.receiveShadow = true;
  scene.add(ground);

  const baseMaterial = new THREE.MeshStandardMaterial({ color: 0x293139, roughness: 0.68, metalness: 0.03 });
  const lidMaterial = new THREE.MeshStandardMaterial({ color: 0x3d4852, roughness: 0.62, metalness: 0.03 });
  const diffuserMaterial = new THREE.MeshPhysicalMaterial({
    color: 0xe7eee7,
    roughness: 0.88,
    metalness: 0,
    transparent: true,
    opacity: 0.62,
    depthWrite: false
  });

  function binaryFromBase64(value) {
    const raw = atob(value);
    const bytes = new Uint8Array(raw.length);
    for (let i = 0; i < raw.length; i++) bytes[i] = raw.charCodeAt(i);
    return bytes.buffer;
  }

  function stlMesh(name, material) {
    const geometry = new THREE.STLLoader().parse(binaryFromBase64(window.EMBEDDED_STL[name]));
    geometry.computeVertexNormals();
    const mesh = new THREE.Mesh(geometry, material);
    mesh.castShadow = true;
    mesh.receiveShadow = true;
    return mesh;
  }

  const base = stlMesh('base', baseMaterial);
  const lid = stlMesh('lid', lidMaterial);
  const diffuser = stlMesh('diffuser', diffuserMaterial);
  const usbInsert = stlMesh('usb_insert', baseMaterial);
  scene.add(base, lid, diffuser, usbInsert);

  const statusLight = new THREE.PointLight(0x22b473, 6.0, 30, 2);
  statusLight.position.set(-10.17, 5.36, 6.0);
  scene.add(statusLight);

  const glowCanvas = document.createElement('canvas');
  glowCanvas.width = 64;
  glowCanvas.height = 64;
  const glowContext = glowCanvas.getContext('2d');
  const glowGradient = glowContext.createRadialGradient(32, 32, 0, 32, 32, 32);
  glowGradient.addColorStop(0, 'rgba(255,255,255,1)');
  glowGradient.addColorStop(0.18, 'rgba(255,255,255,0.8)');
  glowGradient.addColorStop(0.5, 'rgba(255,255,255,0.18)');
  glowGradient.addColorStop(1, 'rgba(255,255,255,0)');
  glowContext.fillStyle = glowGradient;
  glowContext.fillRect(0, 0, 64, 64);
  const ledGlowMaterial = new THREE.SpriteMaterial({
    map: new THREE.CanvasTexture(glowCanvas),
    color: 0x22b473,
    transparent: true,
    blending: THREE.AdditiveBlending,
    depthWrite: false
  });
  const ledGlow = new THREE.Sprite(ledGlowMaterial);
  ledGlow.position.copy(statusLight.position);
  ledGlow.scale.set(5.5, 5.5, 1);
  scene.add(ledGlow);

  const board = new THREE.Group();
  const BOARD_LENGTH = 56.5;
  const BOARD_WIDTH = 27.4;
  const BOARD_BOTTOM = 3.0;
  const BOARD_TOP = BOARD_BOTTOM + 1.65;
  const darkMaterial = new THREE.MeshStandardMaterial({ color: 0x171a1d, roughness: 0.7 });
  const pcbSideMaterial = new THREE.MeshStandardMaterial({ color: 0x181d21, roughness: 0.78 });
  const metalMaterial = new THREE.MeshStandardMaterial({ color: 0xb7babc, roughness: 0.34, metalness: 0.72 });
  const goldMaterial = new THREE.MeshStandardMaterial({ color: 0xb89a56, roughness: 0.4, metalness: 0.62 });
  const whiteMaterial = new THREE.MeshStandardMaterial({ color: 0xe2e4df, roughness: 0.72 });
  const ceramicMaterial = new THREE.MeshStandardMaterial({ color: 0x777364, roughness: 0.58, metalness: 0.12 });
  const ledMaterial = new THREE.MeshStandardMaterial({ color: 0x22b473, emissive: 0x22b473, emissiveIntensity: 1.8, roughness: 0.32 });

  function loadTexture(source) {
    const texture = new THREE.TextureLoader().load(source);
    texture.encoding = THREE.sRGBEncoding;
    texture.anisotropy = renderer.capabilities.getMaxAnisotropy();
    return texture;
  }
  const boardTexture = loadTexture(window.BOARD_ASSETS.board);
  const shieldTexture = loadTexture(window.BOARD_ASSETS.shield);
  const boardTopMaterial = new THREE.MeshStandardMaterial({ map: boardTexture, roughness: 0.62, metalness: 0.04 });
  const shieldTopMaterial = new THREE.MeshStandardMaterial({ map: shieldTexture, roughness: 0.42, metalness: 0.42 });

  function boardBox(size, position, material) {
    const mesh = new THREE.Mesh(new THREE.BoxGeometry(...size), material);
    mesh.position.set(...position);
    mesh.castShadow = true;
    mesh.receiveShadow = true;
    board.add(mesh);
    return mesh;
  }

  function cylinder(radius, height, position, material, segments = 24) {
    const mesh = new THREE.Mesh(new THREE.CylinderGeometry(radius, radius, height, segments), material);
    mesh.rotation.x = Math.PI / 2;
    mesh.position.set(...position);
    mesh.castShadow = true;
    board.add(mesh);
    return mesh;
  }

  function photoPosition(x, y) {
    return [(1198 - y) * BOARD_LENGTH / 1006 - BOARD_LENGTH / 2, BOARD_WIDTH / 2 - (x - 57) * BOARD_WIDTH / 493];
  }

  function componentAtPhoto(x, y, size, height, material) {
    const [px, py] = photoPosition(x, y);
    return boardBox([size[0], size[1], height], [px, py, BOARD_TOP + height / 2], material);
  }

  const pcbShape = new THREE.Shape();
  const x0 = -BOARD_LENGTH / 2;
  const x1 = BOARD_LENGTH / 2;
  const y0 = -BOARD_WIDTH / 2;
  const y1 = BOARD_WIDTH / 2;
  const radius = 0.5;
  pcbShape.moveTo(x0 + radius, y0);
  pcbShape.lineTo(x1 - radius, y0);
  pcbShape.quadraticCurveTo(x1, y0, x1, y0 + radius);
  pcbShape.lineTo(x1, y1 - radius);
  pcbShape.quadraticCurveTo(x1, y1, x1 - radius, y1);
  pcbShape.lineTo(x0 + radius, y1);
  pcbShape.quadraticCurveTo(x0, y1, x0, y1 - radius);
  pcbShape.lineTo(x0, y0 + radius);
  pcbShape.quadraticCurveTo(x0, y0, x0 + radius, y0);
  const pcbGeometry = new THREE.ExtrudeGeometry(pcbShape, { depth: 1.65, bevelEnabled: false, curveSegments: 8 });
  const pcbPositions = pcbGeometry.attributes.position;
  const pcbUvs = pcbGeometry.attributes.uv;
  for (let i = 0; i < pcbPositions.count; i++) {
    pcbUvs.setXY(i, (pcbPositions.getX(i) + BOARD_LENGTH / 2) / BOARD_LENGTH, (pcbPositions.getY(i) + BOARD_WIDTH / 2) / BOARD_WIDTH);
  }
  const pcb = new THREE.Mesh(pcbGeometry, [boardTopMaterial, pcbSideMaterial]);
  pcb.position.z = BOARD_BOTTOM;
  pcb.castShadow = true;
  pcb.receiveShadow = true;
  board.add(pcb);

  boardBox([6.24, 18.0, 0.8], [BOARD_LENGTH / 2 + 3.12, 0.2, BOARD_TOP + 0.4], darkMaterial);
  const [shieldX, shieldY] = photoPosition(285, 358);
  boardBox([18.0, 17.1, 0.35], [shieldX, shieldY, BOARD_TOP + 0.18], goldMaterial);
  const shield = new THREE.Mesh(
    new THREE.BoxGeometry(17.6, 16.8, 2.4),
    [metalMaterial, metalMaterial, metalMaterial, metalMaterial, shieldTopMaterial, metalMaterial]
  );
  shield.position.set(shieldX, shieldY, BOARD_TOP + 1.2);
  shield.castShadow = true;
  board.add(shield);
  const [uflX, uflY] = photoPosition(405, 220);
  cylinder(1.8, 1.2, [uflX, uflY, BOARD_TOP + 3.0], goldMaterial);
  cylinder(0.85, 1.3, [uflX, uflY, BOARD_TOP + 3.1], metalMaterial);

  componentAtPhoto(226, 694, [7.0, 5.0], 1.8, darkMaterial);
  componentAtPhoto(411, 953, [7.0, 7.0], 1.0, darkMaterial);

  for (const y of [605, 700]) {
    componentAtPhoto(386, y, [4.3, 4.8], 1.5, metalMaterial);
    componentAtPhoto(386, y, [3.5, 4.0], 0.35, darkMaterial).position.z = BOARD_TOP + 1.675;
    const [px, py] = photoPosition(386, y);
    cylinder(1.3, 0.35, [px, py, BOARD_TOP + 2.025], darkMaterial);
  }

  const usbFront = -BOARD_LENGTH / 2 - 0.30;
  const usbCenterX = usbFront + 4.0;
  const usbCenterZ = BOARD_TOP + 3.14 / 2;
  for (const y of [-5.915, 5.915]) {
    boardBox([8.0, 8.88, 3.14], [usbCenterX, y, usbCenterZ], metalMaterial);
    boardBox([0.12, 7.2, 1.9], [usbFront - 0.06, y, usbCenterZ], darkMaterial);
    boardBox([0.16, 5.0, 0.55], [usbFront - 0.14, y, usbCenterZ - 0.2], metalMaterial);
  }

  boardBox([5.2, 5.2, 0.8], [-10.17, 5.36, BOARD_TOP + 0.4], whiteMaterial);
  cylinder(1.5, 0.35, [-10.17, 5.36, BOARD_TOP + 0.95], ledMaterial);
  componentAtPhoto(211, 605, [3.0, 5.0], 1.0, ceramicMaterial);
  componentAtPhoto(211, 785, [3.0, 5.0], 1.0, ceramicMaterial);
  scene.add(board);

  const palettes = {
    graphite: [0x293139, 0x3d4852],
    chalk: [0xc8c2b7, 0xebe6dc],
    ocean: [0x29465f, 0x466f91],
    clay: [0x9e5f4d, 0xc1816b]
  };
  const states = {
    free: { color: 0x22b473, label: 'Свободен' },
    busy: { color: 0x347feb, label: 'Занят' },
    call: { color: 0xeb4b4b, label: 'Звонок' },
    off: { color: 0x000000, label: 'Выключен' }
  };

  let mode = 'assembled';
  let currentState = 'free';
  const explode = document.getElementById('explode');
  const showBoard = document.getElementById('show-board');
  const hideLid = document.getElementById('hide-lid');

  function updateLayout() {
    const spread = mode === 'exploded' ? Math.max(Number(explode.value), 22) : Number(explode.value);
    const printing = mode === 'print';
    base.position.set(0, 0, 0);
    lid.rotation.x = printing ? 0 : Math.PI;
    diffuser.rotation.x = printing ? 0 : Math.PI;
    usbInsert.rotation.y = printing ? 0 : Math.PI / 2;
    lid.position.set(0, printing ? 45 : 0, printing ? 0 : 16.2 + spread);
    diffuser.position.set(printing ? 62 : 0, 0, printing ? 0 : 17 + spread * 1.45);
    usbInsert.position.set(printing ? -48 : -31.5 - spread * 0.45, printing ? 45 : 0, 0);
    board.visible = !printing && showBoard.checked;
    lid.visible = !hideLid.checked;
    diffuser.visible = !hideLid.checked;
    statusLight.visible = board.visible;
    ledGlow.visible = board.visible && currentState !== 'off';
  }

  function setMode(nextMode) {
    mode = nextMode;
    document.querySelectorAll('[data-mode]').forEach(button => {
      button.classList.toggle('active', button.dataset.mode === mode);
    });
    if (mode === 'assembled') explode.value = 0;
    if (mode === 'exploded' && Number(explode.value) < 22) explode.value = 26;
    if (mode === 'print') hideLid.checked = false;
    updateLayout();
    resetView();
  }

  function setState(state) {
    currentState = state;
    const color = states[state].color;
    ledMaterial.color.setHex(state === 'off' ? 0x65706a : color).convertSRGBToLinear();
    ledMaterial.emissive.setHex(color).convertSRGBToLinear();
    ledMaterial.emissiveIntensity = state === 'off' ? 0 : 1.8;
    ledGlowMaterial.color.setHex(color).convertSRGBToLinear();
    ledGlow.visible = board.visible && state !== 'off';
    statusLight.color.setHex(color).convertSRGBToLinear();
    statusLight.intensity = state === 'off' ? 0 : 6.0;
    document.querySelectorAll('[data-state]').forEach(button => {
      button.classList.toggle('active', button.dataset.state === state);
    });
    const pill = document.getElementById('state-pill');
    pill.className = `state-pill ${state}`;
    pill.textContent = states[state].label;
  }

  function resetView() {
    if (mode === 'exploded') {
      camera.position.set(120, -137, 114);
      controls.target.set(3.5, 0, 23);
    } else if (mode === 'print') {
      camera.position.set(114, -137, 118);
      controls.target.set(8, 17, 1);
    } else {
      camera.position.set(94, -101, 78);
      controls.target.set(3.5, 0, 6);
    }
    controls.update();
  }

  document.querySelectorAll('[data-mode]').forEach(button => {
    button.addEventListener('click', () => setMode(button.dataset.mode));
  });
  document.querySelectorAll('[data-state]').forEach(button => {
    button.addEventListener('click', () => setState(button.dataset.state));
  });
  document.getElementById('palette').addEventListener('change', event => {
    const colors = palettes[event.target.value];
    baseMaterial.color.setHex(colors[0]);
    lidMaterial.color.setHex(colors[1]);
  });
  explode.addEventListener('input', updateLayout);
  showBoard.addEventListener('change', updateLayout);
  hideLid.addEventListener('change', updateLayout);
  document.getElementById('auto-rotate').addEventListener('change', event => {
    controls.autoRotate = event.target.checked;
  });
  document.getElementById('reset-view').addEventListener('click', resetView);

  function resize() {
    const width = container.clientWidth;
    const height = container.clientHeight;
    renderer.setSize(width, height);
    camera.aspect = width / height;
    camera.updateProjectionMatrix();
  }
  new ResizeObserver(resize).observe(container);
  resize();
  resetView();
  updateLayout();
  setState(currentState);

  function animate() {
    requestAnimationFrame(animate);
    controls.update();
    renderer.render(scene, camera);
  }
  animate();
})();
