// SPDX-License-Identifier: Apache-2.0
// Structural input contract: SimulationFrame satisfies this without a runtime import.
export type Vec3 = readonly [number, number, number];
export type Quat = readonly [number, number, number, number];
export type GoalFrame = {
  time: number;
  links: {body: {position: Vec3; quaternion: Quat}};
  metrics: {fall: boolean};
};
