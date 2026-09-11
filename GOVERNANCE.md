# Project governance

MicroDuckling is a community hobby robotics project maintained by [itchson](https://github.com/itchson). The aim is a small, affordable robot that is approachable to build, repair and understand, with a path toward learning locomotion in NVIDIA Isaac Sim.

The repository begins with the R05 design prototype. Publishing it invites collaboration; it does not turn the current CAD into a qualified kit or establish successful walking.

## Roles and decisions

Anyone can report results, propose ideas, review changes or submit a pull request. The maintainer currently manages the repository, reviews and merges changes, sets release scope and moderates project spaces. There is no formal steering committee, membership requirement or voting process.

Technical decisions should be discussed in issues and pull requests so that contributors can follow the reasoning. Small changes can be proposed directly in a pull request. For changes that affect compatibility, cost, component availability or several subsystems, describe the alternatives and consequences early.

The maintainer makes the final decision on what enters the main repository. Review weighs:

- Evidence from reproducible checks and physical measurements.
- Build difficulty, part availability, cost and repairability.
- Compatibility with the rest of the robot and the effort to maintain the change.
- Clear documentation of assumptions, tradeoffs and remaining unknowns.

A promising idea may remain a branch or experiment until there is enough evidence to adopt it. Contributors can disagree respectfully, offer more evidence or continue an alternative in their own fork under the applicable licenses.

## Releases and project direction

The [roadmap](ROADMAP.md) describes intended stages, not delivery commitments. Priorities may change as physical builds expose problems or contributors bring new evidence. There are no promised review times or release dates.

Release notes should identify the design revision, relevant changes and checks actually performed. Hardware fit, electrical operation, simulation execution, training and physical walking are separate claims and should be reported separately. A result on one component batch or test surface should not be presented as universal.

If the contributor community grows, repository access and additional maintainer roles can be discussed publicly and documented here. This document reflects the current arrangement rather than a promised future organization.

## Participation and questions

Use an issue or pull request for project questions and proposals. Follow the [contribution guide](CONTRIBUTING.md) and [community conduct guidelines](CODE_OF_CONDUCT.md). For a concern that should not be public, consult the contact options available on the maintainer's GitHub profile; do not put private information in an issue.
