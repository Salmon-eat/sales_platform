import * as THREE from "three";
import { RoomEnvironment } from "three/examples/jsm/environments/RoomEnvironment.js";
import { RoundedBoxGeometry } from "three/examples/jsm/geometries/RoundedBoxGeometry.js";

import { HERO_SECTION_EVENT } from "./heroEvents";

/** The site's palette for the clay objects. */
const C = {
  orange: 0xff6a1a,
  orangeLight: 0xff8f52,
  orangeDeep: 0xe0560f,
  graphite: 0x2a2d35,
  graphiteSoft: 0x3a3e48,
  sand: 0xe9ddc8,
  sandDeep: 0xd9cab0,
  brass: 0xf2b72e,
  glass: 0x33404f,
  cream: 0xfff8ee,
};

/** One world unit is this many pixels at scale 1, whatever the height of the hero. */
const PX_PER_UNIT = 40;
/** Half the width of the middle kept free for the title and the search box, in pixels. */
const CLEAR_HALF = 540;
/** A narrow lens: the hero is very wide and low, so a wide one stretches the objects near the screen edges. */
const FOV = 10;

/** A clay material in one colour; a lower roughness makes it shinier (glass, brass). */
type Material = (color: number, roughness?: number) => THREE.MeshStandardMaterial;

const box = (w: number, h: number, d: number, r: number) => new RoundedBoxGeometry(w, h, d, 4, r);

function mesh(geometry: THREE.BufferGeometry, material: THREE.Material, x = 0, y = 0, z = 0) {
  const m = new THREE.Mesh(geometry, material);
  m.position.set(x, y, z);
  return m;
}

function briefcase(m: Material) {
  const g = new THREE.Group();
  g.add(mesh(box(2.4, 1.7, 0.95, 0.28), m(C.orange)));
  g.add(mesh(box(2.44, 0.16, 0.99, 0.07), m(C.orangeDeep), 0, 0.12));
  g.add(mesh(box(0.38, 0.32, 0.14, 0.06), m(C.cream), 0, 0.12, 0.5));
  g.add(mesh(new THREE.TorusGeometry(0.42, 0.1, 14, 32, Math.PI), m(C.graphite), 0, 0.82));
  return g;
}

/** The glass house of the car seen from the side: a raked windscreen at the front (+x), a shorter rear
 * window, extruded across the width and rounded at the edges. */
function carCabin(bottomBack: number, bottomFront: number, topBack: number, topFront: number, height: number, width: number) {
  const side = new THREE.Shape();
  side.moveTo(bottomBack, 0);
  side.lineTo(bottomFront, 0);
  side.lineTo(topFront, height);
  side.lineTo(topBack, height);
  side.closePath();
  const bevel = 0.06;
  const geometry = new THREE.ExtrudeGeometry(side, {
    depth: width - bevel * 2,
    bevelEnabled: true,
    bevelThickness: bevel,
    bevelSize: bevel,
    bevelSegments: 4,
    curveSegments: 1,
  });
  geometry.translate(0, 0, -(width - bevel * 2) / 2);
  return geometry;
}

function car(m: Material) {
  const g = new THREE.Group();
  g.add(mesh(box(2.8, 0.75, 1.35, 0.3), m(C.orange), 0, 0));
  // the upper part: tinted glass all round, a roof on top, pillars between the windows, mirrors
  g.add(mesh(carCabin(-1.0, 0.72, -0.72, 0.12, 0.5, 1.14), m(C.glass, 0.18), 0, 0.33));
  g.add(mesh(box(0.98, 0.1, 1.22, 0.045), m(C.orange), -0.3, 0.86));
  g.add(mesh(box(0.12, 0.52, 1.2, 0.04), m(C.orange), -0.28, 0.6));
  // the slanted pillars run along the edges of the windscreen and the rear window, on both sides
  const pillar = (x: number, length: number, lean: number) => {
    for (const z of [-0.57, 0.57]) {
      const p = mesh(box(0.1, length, 0.1, 0.04), m(C.orange), x, 0.58, z);
      p.rotation.z = lean;
      g.add(p);
    }
  };
  pillar(0.42, 0.8, Math.atan2(0.6, 0.5));
  pillar(-0.86, 0.58, -Math.atan2(0.28, 0.5));
  for (const z of [-0.68, 0.68]) g.add(mesh(box(0.1, 0.1, 0.14, 0.04), m(C.orange), 0.58, 0.45, z));
  for (const z of [-0.4, 0.4]) g.add(mesh(box(0.1, 0.18, 0.3, 0.04), m(C.cream), 1.38, 0.08, z));
  for (const z of [-0.45, 0.45]) g.add(mesh(box(0.08, 0.14, 0.24, 0.04), m(C.orangeDeep), -1.38, 0.1, z));
  const wheel = new THREE.CylinderGeometry(0.34, 0.34, 0.26, 28);
  const hub = new THREE.CylinderGeometry(0.14, 0.14, 0.28, 20);
  for (const x of [-0.85, 0.85]) {
    for (const z of [-0.62, 0.62]) {
      const w = mesh(wheel, m(C.graphite), x, -0.38, z);
      const h = mesh(hub, m(C.sand), x, -0.38, z);
      w.rotation.x = h.rotation.x = Math.PI / 2;
      g.add(w, h);
    }
  }
  return g;
}

function houseKey(m: Material) {
  const g = new THREE.Group();
  const brass = m(C.brass, 0.4);
  g.add(mesh(new THREE.TorusGeometry(0.5, 0.2, 16, 40), brass, -0.6, 0.35));
  g.add(mesh(box(1.9, 0.3, 0.22, 0.1), brass, 0.7, 0.35));
  g.add(mesh(box(0.2, 0.36, 0.22, 0.06), brass, 1.25, 0.1));
  g.add(mesh(box(0.2, 0.26, 0.22, 0.06), brass, 1.55, 0.14));
  const ring = mesh(new THREE.TorusGeometry(0.2, 0.05, 10, 24), m(C.graphite), -1.02, -0.2);
  ring.rotation.y = Math.PI / 2;
  g.add(ring);
  g.add(mesh(box(0.72, 0.56, 0.34, 0.08), m(C.orange), -1.02, -0.95));
  const roof = mesh(new THREE.ConeGeometry(0.6, 0.42, 4), m(C.orangeDeep), -1.02, -0.47);
  roof.rotation.y = Math.PI / 4;
  g.add(roof);
  g.add(mesh(box(0.2, 0.3, 0.06, 0.03), m(C.cream), -1.02, -1.08, 0.18));
  return g;
}

function wrench(m: Material) {
  const g = new THREE.Group();
  g.add(mesh(box(0.36, 2.1, 0.22, 0.1), m(C.graphite), 0, -0.25));
  g.add(mesh(box(0.46, 1.0, 0.3, 0.12), m(C.orange), 0, -0.7));
  // an open jaw: a ring with a quarter cut away at the top
  const jaw = mesh(new THREE.TorusGeometry(0.42, 0.17, 12, 28, Math.PI * 1.5), m(C.graphite), 0, 1.1);
  jaw.rotation.z = Math.PI * 0.75;
  g.add(jaw);
  g.add(mesh(new THREE.TorusGeometry(0.2, 0.09, 10, 24), m(C.graphite), 0, -1.45));
  return g;
}

function sofa(m: Material) {
  const g = new THREE.Group();
  g.add(mesh(box(2.6, 0.55, 1.1, 0.2), m(C.sand), 0, -0.2));
  g.add(mesh(box(2.4, 0.85, 0.36, 0.16), m(C.sandDeep), 0, 0.35, -0.4));
  for (const x of [-1.25, 1.25]) g.add(mesh(box(0.38, 0.8, 1.12, 0.16), m(C.sandDeep), x, 0.05));
  g.add(mesh(box(1.02, 0.26, 0.82, 0.12), m(C.orange), -0.53, 0.18, 0.08));
  g.add(mesh(box(1.02, 0.26, 0.82, 0.12), m(C.orangeLight), 0.53, 0.18, 0.08));
  const leg = new THREE.CylinderGeometry(0.07, 0.05, 0.22, 10);
  for (const x of [-1.15, 1.15]) for (const z of [-0.4, 0.4]) g.add(mesh(leg, m(C.graphite), x, -0.57, z));
  return g;
}

function shop(m: Material) {
  const g = new THREE.Group();
  g.add(mesh(box(2.2, 1.45, 1.2, 0.14), m(C.cream), 0, -0.25));
  g.add(mesh(box(2.34, 0.16, 1.34, 0.06), m(C.sandDeep), 0, 0.55));
  g.add(mesh(box(0.8, 0.56, 0.06, 0.03), m(C.sand), -0.45, -0.2, 0.61));
  g.add(mesh(box(0.5, 0.92, 0.06, 0.03), m(C.graphite), 0.5, -0.5, 0.61));
  // the striped awning over the front, as on a Spanish street
  for (let i = 0; i < 5; i++) {
    const stripe = mesh(box(0.46, 0.12, 0.72, 0.05), m(i % 2 ? C.cream : C.orange), -0.96 + i * 0.48, 0.4, 0.72);
    stripe.rotation.x = 0.45;
    g.add(stripe);
  }
  return g;
}

function paw(m: Material) {
  const g = new THREE.Group();
  const pad = mesh(new THREE.SphereGeometry(0.75, 28, 20), m(C.graphite), 0, -0.35);
  pad.scale.set(1, 0.8, 0.45);
  g.add(pad);
  const toe = new THREE.SphereGeometry(0.3, 20, 14);
  for (const [x, y] of [[-0.8, 0.3], [-0.3, 0.7], [0.3, 0.7], [0.8, 0.3]]) {
    const t = mesh(toe, m(C.graphite), x, y);
    t.scale.set(1, 1.2, 0.55);
    g.add(t);
  }
  return g;
}

function gradCap(m: Material) {
  const g = new THREE.Group();
  g.add(mesh(new THREE.CylinderGeometry(0.62, 0.55, 0.55, 28), m(C.graphiteSoft), 0, -0.25));
  const board = mesh(box(1.9, 0.1, 1.9, 0.04), m(C.graphite), 0, 0.06);
  board.rotation.y = Math.PI / 4;
  g.add(board);
  g.add(mesh(new THREE.SphereGeometry(0.09, 12, 10), m(C.orange), 0, 0.14));
  const cord = mesh(new THREE.CylinderGeometry(0.03, 0.03, 1.05, 8), m(C.orange), 0.52, 0.13);
  cord.rotation.z = Math.PI / 2;
  g.add(cord);
  g.add(mesh(new THREE.CylinderGeometry(0.03, 0.03, 0.55, 8), m(C.orange), 1.04, -0.14));
  g.add(mesh(new THREE.ConeGeometry(0.1, 0.3, 12), m(C.orange), 1.04, -0.5));
  return g;
}

function megaphone(m: Material) {
  const g = new THREE.Group();
  const cone = mesh(new THREE.CylinderGeometry(0.75, 0.28, 1.6, 28), m(C.orange), 0.1);
  cone.rotation.z = -Math.PI / 2; // the wide end looks to the right
  g.add(cone);
  const rim = mesh(new THREE.TorusGeometry(0.75, 0.08, 10, 32), m(C.orangeLight), 0.9);
  rim.rotation.y = Math.PI / 2;
  g.add(rim);
  const back = mesh(new THREE.CylinderGeometry(0.3, 0.3, 0.35, 20), m(C.graphite), -0.85);
  back.rotation.z = Math.PI / 2;
  g.add(back);
  g.add(mesh(box(0.22, 0.62, 0.22, 0.08), m(C.graphite), -0.35, -0.55));
  return g;
}

type Spec = {
  key: string;
  build: (m: Material) => THREE.Group;
  /** -1 left of the search, 1 right of it */
  side: -1 | 1;
  /** how far into the free side, 0 at the search box, 1 at the screen edge */
  across?: number;
  /** or, instead, over the middle: this many pixels from the centre, beside the title or under the search */
  inner?: number;
  /** height, -1 bottom of the hero, 1 top */
  up: number;
  /** toward the viewer; below zero the object sits further back and melts into the background */
  depth: number;
  scale: number;
  turn: [number, number, number];
};

const SPECS: Spec[] = [
  // scattered over the whole hero: the free sides, beside the title, under the search
  { key: "empleo", build: briefcase, side: -1, across: 0.22, up: 0.32, depth: 0, scale: 0.9, turn: [0.2, 0.5, 0.05] },
  { key: "inmobiliaria", build: houseKey, side: -1, across: 0.62, up: -0.42, depth: 0.6, scale: 0.8, turn: [0.15, 0.3, -0.35] },
  { key: "negocios", build: shop, side: -1, across: 0.92, up: 0.5, depth: -2, scale: 0.6, turn: [0.2, 0.5, 0] },
  { key: "animales", build: paw, side: -1, inner: 410, up: 0.6, depth: -1.5, scale: 0.45, turn: [0.1, 0.3, 0.3] },
  { key: "formacion-sec", build: gradCap, side: -1, inner: 330, up: -0.72, depth: -1.5, scale: 0.5, turn: [0.35, 0.4, 0.1] },
  { key: "motor", build: car, side: 1, across: 0.3, up: 0.02, depth: 0.5, scale: 1, turn: [0.18, -0.6, 0] },
  { key: "articulos", build: sofa, side: 1, across: 0.84, up: -0.42, depth: 0.2, scale: 0.75, turn: [0.3, -0.45, 0] },
  { key: "comunidad", build: megaphone, side: 1, inner: 420, up: 0.62, depth: -1.5, scale: 0.45, turn: [0.1, -0.5, 0.25] },
  { key: "servicios-sec", build: wrench, side: 1, inner: 360, up: -0.72, depth: -1, scale: 0.45, turn: [0.1, 0.3, -1.25] },
];

type Item = {
  spec: Spec;
  rig: THREE.Group;
  body: THREE.Group;
  shadow: THREE.Mesh<THREE.PlaneGeometry, THREE.MeshBasicMaterial>;
  materials: THREE.MeshStandardMaterial[];
  phase: number;
  focus: number;
  fade: number;
};

function shadowTexture() {
  const canvas = document.createElement("canvas");
  canvas.width = canvas.height = 128;
  const ctx = canvas.getContext("2d")!;
  const gradient = ctx.createRadialGradient(64, 64, 0, 64, 64, 64);
  gradient.addColorStop(0, "rgba(22,24,29,0.55)");
  gradient.addColorStop(1, "rgba(22,24,29,0)");
  ctx.fillStyle = gradient;
  ctx.fillRect(0, 0, 128, 128);
  return new THREE.CanvasTexture(canvas);
}

/** Puts the floating section objects into `container` and returns the function that removes them. */
export function mountHeroScene(container: HTMLElement): () => void {
  let renderer: THREE.WebGLRenderer;
  try {
    renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true, powerPreference: "low-power" });
  } catch {
    return () => undefined; // no WebGL: the hero simply stays plain
  }
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 1.75));
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  container.appendChild(renderer.domElement);

  const scene = new THREE.Scene();
  const pmrem = new THREE.PMREMGenerator(renderer);
  const room = new RoomEnvironment();
  scene.environment = pmrem.fromScene(room, 0.04).texture;
  scene.environmentIntensity = 0.55;
  scene.add(new THREE.HemisphereLight(0xfff6ea, 0xd9c8ae, 1.4));
  const sun = new THREE.DirectionalLight(0xfff0dd, 2.2);
  sun.position.set(-5, 8, 6);
  scene.add(sun);

  const camera = new THREE.PerspectiveCamera(FOV, 1, 0.1, 200);
  const fog = new THREE.Fog(0xf6f2ea, 10, 20);
  scene.fog = fog;
  // the fog takes the hero's own background, and follows the light / dark switch
  const paint = () => {
    const color = getComputedStyle(container.parentElement ?? container).backgroundColor;
    if (color && !color.startsWith("rgba(0, 0, 0, 0")) fog.color.setStyle(color, THREE.SRGBColorSpace);
  };
  paint();
  const theme = new MutationObserver(paint);
  theme.observe(document.documentElement, { attributes: true, attributeFilter: ["data-theme", "class"] });
  const shadowMap = shadowTexture();
  const shadowGeometry = new THREE.PlaneGeometry(3.2, 3.2);

  const items: Item[] = SPECS.map((spec, index) => {
    const materials: THREE.MeshStandardMaterial[] = [];
    const cache = new Map<string, THREE.MeshStandardMaterial>();
    const material: Material = (color, roughness = 0.62) => {
      const key = `${color}:${roughness}`;
      let found = cache.get(key);
      if (!found) {
        found = new THREE.MeshStandardMaterial({ color, roughness, metalness: 0, transparent: true });
        cache.set(key, found);
        materials.push(found);
      }
      return found;
    };
    const rig = new THREE.Group();
    const body = spec.build(material);
    const shadow = new THREE.Mesh(
      shadowGeometry,
      new THREE.MeshBasicMaterial({ map: shadowMap, transparent: true, depthWrite: false }),
    );
    shadow.rotation.x = -Math.PI / 2;
    shadow.position.y = -1.6;
    rig.add(body, shadow);
    scene.add(rig);
    return { spec, rig, body, shadow, materials, phase: index * 2.1, focus: 0, fade: 1 };
  });

  let width = 0;
  let height = 0;
  let unit = 1; // how big the objects are on this screen
  const layout = () => {
    width = container.clientWidth;
    height = container.clientHeight;
    if (!width || !height) return;
    renderer.setSize(width, height, false);
    camera.aspect = width / height;
    const distance = height / PX_PER_UNIT / 2 / Math.tan(THREE.MathUtils.degToRad(FOV / 2));
    camera.position.set(0, distance * 0.16, distance);
    camera.lookAt(0, 0, 0);
    camera.updateProjectionMatrix();
    // the objects further back fade into the page colour, the way far things do in air
    fog.near = distance - 1;
    fog.far = distance + 7;
    const free = width / 2 - CLEAR_HALF;
    unit = THREE.MathUtils.clamp(free / 300, 0.5, 1.15);
    for (const item of items) item.rig.visible = free > 75;
  };
  layout();
  const resize = new ResizeObserver(layout);
  resize.observe(container);

  let chosen: string | null = null;
  const onSection = (event: Event) => {
    chosen = (event as CustomEvent<string | null>).detail || null;
  };
  window.addEventListener(HERO_SECTION_EVENT, onSection);

  const pointer = { x: 0, y: 0, tx: 0, ty: 0 };
  const onMove = (event: PointerEvent) => {
    pointer.tx = (event.clientX / window.innerWidth) * 2 - 1;
    pointer.ty = (event.clientY / window.innerHeight) * 2 - 1;
  };
  window.addEventListener("pointermove", onMove, { passive: true });

  let visible = true;
  let frame = 0;
  let last = performance.now();
  let shown = false;
  const tick = (now: number) => {
    frame = 0;
    const dt = Math.min((now - last) / 1000, 0.05);
    last = now;
    const t = now / 1000;
    const ease = 1 - Math.exp(-dt * 5);
    pointer.x += (pointer.tx - pointer.x) * ease;
    pointer.y += (pointer.ty - pointer.y) * ease;

    const free = width / 2 - CLEAR_HALF;
    for (const item of items) {
      const { spec } = item;
      const mine = chosen === spec.key;
      item.focus += ((mine ? 1 : 0) - item.focus) * ease;
      item.fade += ((chosen && !mine ? 0.28 : 1) - item.fade) * ease;

      const near = 1 + spec.depth * 0.35;
      const bob = Math.sin(t * 0.7 + item.phase) * 0.18;
      // never closer to the screen edge than an object's own half width
      const across =
        spec.inner ?? Math.min(CLEAR_HALF + free * (spec.across ?? 0.5), width / 2 - (62 * spec.scale + 12) * unit);
      const x = (spec.side * across) / PX_PER_UNIT;
      const y = (spec.up * height) / 2 / PX_PER_UNIT;
      // a chosen object comes nearer, so it also moves in a little, or perspective pushes it off the edge;
      // one at the side also rises to the middle, one over the middle stays clear of the search
      item.rig.position.set(
        x * (1 - item.focus * 0.06) + pointer.x * 0.35 * near,
        y * (1 - item.focus * (spec.inner ? 0 : 0.6)) + bob,
        spec.depth + item.focus * 1.4,
      );
      const size = spec.scale * unit * (1 + item.focus * 0.3) * (chosen && !mine ? 0.85 : 1);
      item.rig.scale.setScalar(size);
      item.shadow.position.y = -1.6 - bob;
      item.shadow.material.opacity = (0.55 - bob * 0.8) * item.fade;

      const [rx, ry, rz] = spec.turn;
      item.body.rotation.set(
        rx + Math.sin(t * 0.5 + item.phase) * 0.08 + pointer.y * 0.2,
        ry + Math.sin(t * 0.35 + item.phase) * 0.3 + pointer.x * 0.4 + item.focus * Math.sin(t * 0.9) * 0.25,
        rz + Math.cos(t * 0.45 + item.phase) * 0.05,
      );
      for (const material of item.materials) material.opacity = item.fade;
    }

    renderer.render(scene, camera);
    if (!shown) {
      shown = true;
      container.classList.add("is-ready");
    }
    if (visible && !document.hidden) frame = requestAnimationFrame(tick);
  };
  const run = () => {
    if (!frame && visible && !document.hidden) {
      last = performance.now();
      frame = requestAnimationFrame(tick);
    }
  };
  run();

  // no drawing while the hero is scrolled away or the tab is in the background
  const watch = new IntersectionObserver(([entry]) => {
    visible = entry.isIntersecting;
    run();
  });
  watch.observe(container);
  document.addEventListener("visibilitychange", run);

  return () => {
    cancelAnimationFrame(frame);
    watch.disconnect();
    resize.disconnect();
    theme.disconnect();
    document.removeEventListener("visibilitychange", run);
    window.removeEventListener(HERO_SECTION_EVENT, onSection);
    window.removeEventListener("pointermove", onMove);
    scene.traverse((node) => {
      if (node instanceof THREE.Mesh) {
        node.geometry.dispose();
        (node.material as THREE.Material).dispose();
      }
    });
    shadowMap.dispose();
    scene.environment?.dispose();
    pmrem.dispose();
    renderer.dispose();
    renderer.domElement.remove();
  };
}
