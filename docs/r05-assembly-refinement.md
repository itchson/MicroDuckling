# R05 assembly refinement

Historical revision; see [R06 changes](r06-simplified-design.md) for the current build.

R05 retains the compact R04 head, torso proportions and four MG90S joints. It addresses assembly defects identified in the saved nominal CAD. It remains an engineering prototype without physical fit, powered operation or walking validation.

| Area | R05 change | Remaining qualification |
|---|---|---|
| Controller clearance | Relieves the left shell's internal locating lip near the terminal and PCB edge; nominal gap increases from 0.388 mm to about 1.23 mm. The 1.3 mm outer wall stays unchanged. | Actual fitted connector envelope, print tolerances and shell flex. |
| Rear access | Extends a previously incomplete cutter through the rear wall and lip. Nominal opening is 14 × 10 mm; an 8 × 4 mm straight probe passes through both halves. | Actual plug insertion, disconnect and strain relief. |
| Battery restraint | Repositions 3.6 mm slots away from a supporting pedestal; models 3 mm tape with a 7 mm lap and a 22 × 42 × 0.7 mm insulating pad. | Tape material, overlap fastening, compression, pack fit and removable retention. |
| Head wiring | Replaces routes through the mouth mechanism with three indicative 0.84 mm corridors toward the ESP32 header region; extends the carrier notch. | Full conductor count, actual insulation, plugs, bend radius and neck-yaw service loop. |
| Camera flex | Routes from the FFC region toward the sensor while clearing the nominal SD cage, tray and cradle. | Actual flex length, latch seating and motion without crease or tension. |

The nominal mass estimate is **257.28 g**. Neutral global COM is approximately **(0.19, 0.57, 57.23) mm**, with the hip axis at X = 0. The overall envelope remains **76 × 112 × 136 mm**. There are 14 robot prints and two fit coupons. These values include estimated purchased hardware and full-density printed solids; they are not measurements of a built robot.

Public viewer geometry omits four detailed vendor-derived board models. The mass metadata still describes the full intended assembly. Displayed geometry volume must not be used to recompute that complete mass estimate.

Read the [engineering review](engineering-review.md) for exactly what was checked and the [assembly guide](design-and-assembly.md) before using the nominal hardware dimensions.
