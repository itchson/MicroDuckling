# License scope and publication boundaries

MicroDuckling uses per-asset licenses. Original source, documentation and independently generated mechanical designs use the [Apache License 2.0](../LICENSE). That license does not replace the Adafruit hardware license or the MIT notices on adapted shadcn UI files.

| Published material | License and scope |
|---|---|
| Mechanical native CAD, printed-part exports and original mechanical viewer meshes | Apache-2.0. These exports exclude the four separately supplied electronics visuals. |
| `components/meshes/IMU.json` and `ServoController.json` | CC-BY-SA-3.0 adaptations of Adafruit PCB designs. |
| `components/meshes/Buck_0.json` and `Buck_1.json` | Apache-2.0 original visual approximations of Pololu regulators, authored from dimensions and generic primitives; not conversions of manufacturer STEP files. |
| Electronics-inclusive assembled/exploded renders and their thumbnails | CC-BY-SA-3.0 composite artwork; retain the Adafruit and MicroDuckling credits below. This does not relicense the separate mechanical source files. |
| Adapted shadcn UI files | MIT; exact paths are listed in [third-party notices](../THIRD_PARTY_NOTICES.md). |
| AI-generated mascot in `assets/brand/` | Offered separately under Apache-2.0; see its [provenance](../assets/brand/PROVENANCE.md). It is not part of the Adafruit-derived artwork. |

The two Adafruit designs are by **Limor Fried/Ladyada for Adafruit Industries**. MicroDuckling contributors adapted Eagle outlines, holes, pads and package positions into colored 3D meshes, added approximate component heights and fitted connectors, and positioned the boards in the robot. These are adaptations, not manufacturer mechanical CAD. [Component attribution](../components/NOTICE.json) records source titles, URLs, hashes and changes; complete upstream READMEs and licenses are preserved under `components/licenses/`. Adafruit's hardware notices select [CC-BY-SA 3.0](https://creativecommons.org/licenses/by-sa/3.0/). The additional LSM6DS3 MIT notice is retained and is not treated as an override of those hardware terms.

The viewer combines separately licensed component records with the mechanical assets. Keep the component notices and license information when redistributing that collection. Assembled/exploded image assets incorporating the Adafruit adaptations, including derivative thumbnails, are distributed as CC-BY-SA-3.0 composites. Credit MicroDuckling contributors for the robot, adaptations and rendering, and Limor Fried/Ladyada for Adafruit Industries for the two board designs; link the [component notice](../components/NOTICE.json) and license. [Render provenance](../assets/renders/render_provenance.json) identifies the assets and their inputs. A format change or rasterization does not remove upstream rights.

Pololu's manufacturer STEP models remain local reference inputs: no general redistribution grant was established for those downloaded files. The public regulator visuals use independently authored boxes, cylinders, holes and generic component arrangements informed by published dimensions and photographs. They include no manufacturer STEP geometry, photograph, drawing image, logo or silkscreen. Their Apache license covers the new representation, not rights in the commercial hardware or its trademarks.

Microduck is the inspiration, with credit to Pollen Robotics and Hugging Face. Its repositories provide Apache-licensed software, while Pollen's [press kit](https://pollen-robotics.com/microduck/press-kit/) limits the open-source statement to software. This repository distributes no official Microduck meshes, policies, product photography or branding. It is an independent hobby project with no upstream affiliation or endorsement.

Installed dependencies retain their own licenses, including the Apache-2.0 [Rapier physics engine](https://github.com/dimforge/rapier/blob/master/LICENSE). See [third-party notices](../THIRD_PARTY_NOTICES.md) for details.

Before publishing a changed build, use the public export/validation workflow and retain the per-asset notices. `build/local/` and `references/components_r02/` remain ignored. Full local scenes and generated body-link meshes can still contain manufacturer STEP geometry; restoring separately licensed viewer assets does not authorize publishing those aggregates.
