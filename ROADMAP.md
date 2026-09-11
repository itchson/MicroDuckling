# Roadmap

The aim is a small, affordable hobby robot that is easy to build and rewarding to improve. MicroDuckling is inspired by Hugging Face / Pollen Robotics' Microduck. The longer-term direction is to train locomotion in NVIDIA Isaac Sim and evaluate it on physical hardware.

This is a sequence of learning and validation stages, not a schedule. Work can overlap, and measurements may require changes to earlier designs. Contributions that reduce cost, simplify assembly or make results easier to reproduce are welcome throughout.

## Current baseline: R06 design prototype

- Four MG90S joints, 15 robot print parts and two fit coupons.
- Approximately 248 g estimated total mass; this is not a measured build weight.
- CAD, mesh, sampled motion and assembly-access checks, plus a static simulation scaffold and tests.
- A local browser physics experiment, bounded gait search and synthetic-camera controller experiments; model-based gait and camera-approach tests now pass; physical transfer remains unproven.
- No qualified physical assembly, completed firmware, Isaac Sim runtime or training result, or demonstrated physical walking.

The [engineering review](docs/engineering-review.md) and [R06 notes](docs/r06-simplified-design.md) describe the current checks and exclusions. The following stages describe work still needed.

## 1. Measure the actual hardware

Record dimensions and masses for the actual servos, seated horns, screws, electronics, connectors and battery. Resolve differences between purchased parts, manufacturer references and CAD assumptions. Keep part identity and measuring method with each result.

**Useful outcome:** a completed [measurement worksheet](docs/hardware-measurements.md), a list of discrepancies and CAD updates supported by those measurements.

**Ways to help:** mechanical inspection, component sourcing, measurement photos and clearer worksheets.

## 2. Print and assemble incrementally

Start with fit coupons, then test the affected interfaces and a complete assembly. Check print orientation, fastening, tool access, wire routing, service loops, restraint and disassembly with the actual parts. Record failed fits and changes as carefully as successful ones.

**Useful outcome:** documented print settings and an assembly sequence that someone else can repeat, with remaining fit or strength questions listed and an actual build mass recorded.

**Ways to help:** printing, CAD refinement, assembly documentation and reducing part count or cost.

## 3. Establish the electrical system

Turn the proposed component arrangement into a documented wiring and power design. Resolve connector choices, battery protection and monitoring, servo power disable behavior and strain relief. Measure rail voltage, current and temperature under representative loads, including more than one servo moving.

**Useful outcome:** a reproducible wiring diagram and bench results that support the chosen components and operating limits. Geometric cable corridors alone do not establish a working harness.

**Ways to help:** electronics design, power measurements, wiring layouts and test procedures.

## 4. Bring up firmware and characterize motion

Implement and document controller setup, joint calibration, bounded position commands, rate limits, IMU axes, logging and watchdog / disable behavior. Measure servo direction, range, lag, backlash and loaded response. Establish a control and observation interface that simulation and firmware can share.

**Useful outcome:** repeatable bench bring-up with calibration and logs, including observed behavior after communication loss or reset. Use the measured behavior to replace assumptions in the simulation model.

**Ways to help:** embedded software, instrumentation, calibration tools and actuator characterization.

## 5. Run and evaluate simulation

Confirm a supported Isaac Sim / Isaac Lab setup, import the robot, inspect joints and collisions, and exercise physics before training. Compare the model with measured mass, actuator and contact behavior. Run small training experiments, then evaluate across seeds and held-out parameters with recorded configurations and metrics.

**Useful outcome:** a reproducible Isaac runtime and training workflow, with logs distinguishing import checks, diagnostic motion and learned behavior. The browser parameter search is an early experiment; there is no trained Isaac policy yet.

**Ways to help:** simulation integration, reinforcement learning, system identification and experiment documentation. Start with the [simulation notes](docs/simulation.md), including their version and runtime limitations.

## 6. Evaluate physical locomotion and simplify the build

Bring tested control or policy behavior to the robot through supported, bounded motion trials. Record falls, slip, power behavior, temperatures and performance on stated surfaces. Compare physical behavior with simulation and revise the design or model where they disagree.

**Useful outcome:** repeatable physical walking evidence with the hardware revision, calibration, controller or policy, test conditions and limitations included. Use independent build feedback to improve instructions and work toward a qualified build release.

**Ways to help:** physical testing, sim-to-real analysis, assembly feedback, accessibility and documentation.

See [CONTRIBUTING.md](CONTRIBUTING.md) to share a result or propose a change. A small, well-documented measurement can unblock several of these stages.
