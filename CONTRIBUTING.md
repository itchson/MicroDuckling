# Contributing to MicroDuckling

MicroDuckling aims to become a small, affordable hobby robot that people can build and improve together. It is inspired by Hugging Face / Pollen Robotics' Microduck. This repository starts with an imperfect prototype; practical measurements, clear explanations and small fixes are valuable contributions.

You do not need to own the full robot or know every part of robotics to help. Mechanical design, electronics, firmware, simulation, reinforcement learning, testing and documentation all have open work.

## Start here

Read the [README](README.md) for the current scope and the [roadmap](ROADMAP.md) for the next stages. The R08 prototype uses four MG90S servos with integrated direct-mount sockets, a separate shell-mounted upper-mouth base and two fit coupons. Its complete mass is a CAD estimate. The default 20-tooth socket profile is unverified against the supplied servo batch. Geometry and static simulation checks do not establish physical fit, electrical performance or walking capability.

Useful first contributions include:

- Measure an actual servo, output spline, fastener or board using the [hardware worksheet](docs/hardware-measurements.md).
- Print a fit coupon and report the dimensions, settings and result, including failures.
- Identify an unclear assembly step or reproduce a documented software check.
- Improve a diagram, explanation, setup instruction or translation.
- Propose a lower-cost or easier-to-source part with dimensions and the changes it would require.

Check existing issues and pull requests before starting. You can open an issue to discuss a larger change, or submit a small fix directly. Discussion is useful when a change affects the robot's dimensions, component choices or control interface; it is not a prerequisite for contributing.

## Share evidence that others can use

For hardware work, record the revision or commit, exact part or supplier reference where known, units, measuring method and photos or sketches. Separate catalog values and CAD assumptions from measurements. Do not substitute a nominal value for an unmeasured result. For prints, include material, printer, nozzle, layer height, orientation and any scaling or slicer compensation that affected fit.

For software or simulation work, record the relevant tool versions, commands, expected behavior and actual result. A short reproducible example or focused log is more useful than a large unfiltered dump. Remove credentials, personal information and unrelated local files before uploading anything.

Use the bug / fit report form for a reproducible problem and the proposal form for an idea. Incomplete measurements are welcome: mark unknowns and explain what you did observe.

## Make a focused pull request

1. Fork the repository and create a branch for your change.
2. Edit the source of the affected design, code or document. If you also change generated CAD, meshes or reports, explain how you regenerated them and which source revision they match.
3. Run the checks relevant to the change using the repository's documented setup. Describe what passed, what failed and what you could not run. Documentation-only fixes can be checked by reading the rendered text and following the affected links.
4. Open a pull request describing the problem, the change and the evidence. Link any related issue; an issue is optional.

Keep unrelated changes separate. Include editable source for new designs where possible. Avoid adding dependency folders, caches, temporary exports or large recordings when a small example will explain the result.

For mechanical changes, review [engineering checks and their limits](docs/engineering-review.md) and the [R08 refinement notes](docs/r08-upper-mouth-design.md). A collision check is evidence about the modeled geometry, not proof of strength, cable flexibility or assembly access with real parts. For simulation changes, follow [simulation documentation](docs/simulation.md) and distinguish static validation, an actual Isaac Sim run, training and physical evaluation in your report.

## Credit and review

Share only material you have the right to contribute. Preserve upstream notices and identify the source and license of third-party code, CAD, images or data. See the repository [license](LICENSE); individual imported references may carry their own notices.

[itchson](https://github.com/itchson) currently maintains the project. Review considers reproducibility, ease of building, cost, maintainability and the evidence behind a change. A useful contribution can still need revisions or remain an experiment. The [governance notes](GOVERNANCE.md) explain how decisions are made, and the [code of conduct](CODE_OF_CONDUCT.md) applies to project participation.
