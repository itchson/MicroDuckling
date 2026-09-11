<p align="center">
  <img src="assets/brand/microduckling-mascot.png" alt="MicroDuckling: a white robot duck with a single camera and orange curved feet" width="190">
</p>

<h1 align="center">MicroDuckling</h1>
<p align="center">A little robot to print, build, learn from and improve together.</p>
<p align="center">
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-Apache--2.0-blue" alt="Apache 2.0 license"></a>
  <a href="ROADMAP.md"><img src="https://img.shields.io/badge/status-CAD_prototype-orange" alt="Status: CAD prototype"></a>
  <a href="https://github.com/itchson/MicroDuckling/actions/workflows/checks.yml"><img src="https://github.com/itchson/MicroDuckling/actions/workflows/checks.yml/badge.svg" alt="Repository checks"></a>
</p>

MicroDuckling is an independent hobby robot project inspired by [Microduck from Pollen Robotics / Hugging Face](https://pollen-robotics.com/microduck/). The goal is a **small, affordable robot that people can build with printed parts and accessible electronics**, then make better as a community.

The design pairs a big faceted head and a small white body with smooth orange rocker feet. Four MG90S servos move the left leg, right leg, neck and mouth. Eventually, we want to model and train its behaviour in **NVIDIA Isaac Sim / Isaac Lab**, then bring useful movements to the real robot.

**This is an early CAD prototype, not a proven walking kit.** Contributions that uncover a fit problem, reduce cost, simplify assembly or improve the simulation are part of the project’s purpose.

<p align="center"><img src="assets/renders/assembled.png" alt="Actual R05 mechanical CAD, assembled three-quarter view" width="880"></p>
<p align="center"><em>Actual R05 CAD. The mascot above is an illustration; neither image is a photograph of a working robot.</em></p>

## Where it stands

| Area | Current state |
| --- | --- |
| Mechanical design | R05: 14 robot print parts, two fit coupons, four servo joints |
| Size and mass | About 136 mm tall; 257 g estimated complete mass, not measured |
| CAD checks | Printable mesh checks and sampled clearance reviews completed on the source design |
| Physical assembly | Not yet verified with printed parts and the specified hardware |
| Electronics and firmware | Parts researched; wiring, power tests and robot firmware still need development |
| Walking | Not demonstrated; servo holding, temperature and traction need bench tests |
| Simulation | Source scaffolding and static tests; no validated Isaac runtime or trained policy |
| Affordability | A goal: current research estimate is USD 120–145, plus charger/programmer, shipping and local costs |

Cost estimates are dated research, not current quotes or a promised kit price. See [parts and costs](docs/parts-research.md) and the [engineering review](docs/engineering-review.md).

## Start exploring

- **Inspect the design:** open [the mechanical FreeCAD model](cad/MicroDuckling_R05_mechanical.FCStd) or [the printed-part STEP](cad/MicroDuckling_R05_printed.step).
- **Browse print files:** [STL](cad/stl/) and [3MF](cad/3mf/). Start with the two fit coupons and the [hardware measurement checklist](docs/hardware-measurements.md); a full print is not yet qualified.
- **Understand the assembly:** read the [assembly review](docs/design-and-assembly.md) and [R05 changes](docs/r05-assembly-refinement.md).
- **Work on simulation:** start with the [simulation guide](docs/simulation.md) and [roadmap](ROADMAP.md).

The public mechanical preview omits four supplier board models with separate or unresolved redistribution terms. The physical design still includes the servo controller, IMU and two voltage regulators. The mass estimate describes the **complete intended assembly**. See [license scope and reference inputs](docs/licensing.md).

### Run the CAD viewer locally

Install Node.js 22.18 or newer (Node 24 is used in CI), then:

```sh
git clone https://github.com/itchson/MicroDuckling.git
cd MicroDuckling/viewer
npm ci
npm run dev
```

Open the local address printed in the terminal, normally `http://127.0.0.1:5192`. Orbit the model, select and isolate parts, open the exploded view, inspect the inside and pose the four joints. These controls change the visualization; they do not simulate walking or command hardware. FreeCAD is not required to use the viewer.

<p align="center"><img src="assets/renders/exploded.png" alt="Exploded view of the original MicroDuckling mechanical parts" width="880"></p>

### Develop the design

The [developer guide](docs/development.md) covers the CAD toolchain, optional supplier reference downloads and checks. Parametric Python source lives in [src](src/); the native public model contains editable solids. The source is the place to change design parameters and regenerate geometry.

```sh
python -m pip install -r requirements-dev.txt
python scripts/validate_repository.py
python -m unittest discover -s simulation/tests
cd viewer
npm ci
npm test
npm run build
```

## Help a little duckling grow

You do not need to solve the whole robot to contribute. A measured servo horn, a clearly photographed fit failure, a cheaper power option, a better assembly step or a reproducible simulation result can all help.

Read [CONTRIBUTING](CONTRIBUTING.md), browse the [roadmap](ROADMAP.md), or [open an issue](https://github.com/itchson/MicroDuckling/issues/new/choose). Please include what you actually tested and distinguish measured results from estimates. The [conduct](CODE_OF_CONDUCT.md) and [governance](GOVERNANCE.md) documents explain how we work together.

## License and inspiration

Original MicroDuckling source, documentation and original design exports are provided under [Apache-2.0](LICENSE), subject to the [third-party notices](THIRD_PARTY_NOTICES.md). Supplier files obtained separately retain their own terms. We kept Apache-2.0 for a consistent permissive starting point; a hardware-specific license can be discussed for future contributions without pretending it changes third-party rights.

MicroDuckling is an independent fan project, with its own design and identity. It is not an official Microduck model, a scaled copy of the official CAD, or affiliated with or endorsed by Hugging Face, Pollen Robotics or NVIDIA. Their names identify inspiration and intended tooling. The original mascot was made with OpenAI image generation; its [prompt and provenance](assets/brand/PROVENANCE.md) are included.
