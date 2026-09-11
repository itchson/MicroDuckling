# Local CAD viewer

Run from this directory with Node.js 22.18+ (CI uses Node 24):

```sh
npm ci
npm run dev
```

The terminal prints the local address, normally `http://127.0.0.1:5192`. The app requires a browser with WebGL. It works from the checked-in public CAD snapshot without FreeCAD, supplier downloads, accounts or cloud services.

`npm run prepare:cad` stages the explicitly permitted files from `../cad`, `../assets` and `../docs` into ignored `public/`. Development, tests and builds run this step automatically. Never replace it with a recursive copy of a local engineering workspace: full rebuilds may contain third-party board geometry that is deliberately absent here.

```sh
npm test
npm run build
npm run preview
```

The tests cover joint transforms, visibility, material groups and camera clipping. They do not run a physical simulation or verify browser interactions. The joint sliders pose a kinematic model only. The displayed mass is the full intended robot estimate, including the four supplier boards omitted from this public mechanical view.

UI primitives adapted from shadcn retain their MIT notice; see [third-party notices](../THIRD_PARTY_NOTICES.md).
