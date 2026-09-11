# Local CAD viewer and physics experiment

Run from this directory with Node.js 22.18+ (CI uses Node 24):

```sh
npm ci
npm run dev
```

The terminal prints the local address, normally `http://127.0.0.1:5192`. A WebGL-capable browser is required. FreeCAD, supplier downloads, accounts and cloud services are not required.

The viewer combines 87 mechanical assembly records with four separately licensed electronics visuals; two fit coupons are also available. The parts hierarchy starts collapsed. Orbit, isolation, inside view, an assembly/explosion slider and joint sliders inspect the design. At 100% explosion, conservative mesh bounds have a gap between every component; intermediate positions are an illustration, not a collision-free removal path.

The Simulation tab runs Rapier rigid-body physics and a seeded cross-entropy search over bounded gait parameters. Its synthetic head camera renders 96 × 72 pixels, detects a magenta target and supplies only bearing/area observations to a controller. Camera learning tests bounded controller settings against visibility, centering, apparent-area growth and fall scores. It does not recognize arbitrary objects or connect to an ESP32 camera. Body travel comes from simulation, and none of these controls command hardware. See the [simulation guide](../docs/simulation.md) for assumptions and measured limitations.

`npm run prepare:cad` stages explicitly permitted CAD, component, asset and documentation files into ignored `public/`. Development, tests and builds run this step automatically. Full local engineering builds can contain Pololu STEP-derived geometry that is not approved for publication; retain the explicit staging allowlist.

```sh
npm test
npm run build
npm run preview
```

The automated checks cover geometry transforms, materials, visibility, explosion separation, the headless physics engine, image detection and the actual worker's pose/reset/learning protocol. A separate geometry raycast checks the assembled camera sightline; interactive WebGL rendering still needs browser review. Passing tests does not establish physical walking, actual servo performance or an Isaac runtime result. The displayed mass is the complete intended physical estimate; adding electronics visuals does not add their mass again.

The two Adafruit PCB mesh adaptations retain CC BY-SA 3.0; original mechanical meshes and regulator approximations use Apache-2.0. Adapted shadcn UI primitives retain MIT notices, and installed dependencies retain their licenses, including Apache-2.0 for Rapier. See [third-party notices](../THIRD_PARTY_NOTICES.md).
