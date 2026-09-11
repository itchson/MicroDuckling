// SPDX-License-Identifier: Apache-2.0
// Environment reward/terminal truth. Never pass this state to the image-only actor.
import type {GoalFrame, Quat, Vec3} from './goal-types.ts';

export type GoalConfig = {
  /** Body-link local COM from PhysicsAsset.links.find(l => l.name === 'body').comM. */
  rootLocalComM: Vec3;
  /** Conservative horizontal front envelope measured from the body COM. */
  robotFrontExtentM: number;
  targetHalfWidthM: number;
  minFrontGapM: number;
  maxFrontGapM: number;
  minProgressM: number;
  maxHeadingErrorRad: number;
  maxUprightTiltRad: number;
  holdSeconds: number;
  progressWindowSeconds: number;
};

export const GOAL_DEFAULTS: Omit<GoalConfig, 'rootLocalComM'> = {
  robotFrontExtentM: .060, targetHalfWidthM: .025,
  minFrontGapM: .025, maxFrontGapM: .045,
  minProgressM: .025, maxHeadingErrorRad: 20 * Math.PI / 180,
  maxUprightTiltRad: 15 * Math.PI / 180,
  holdSeconds: 1.5, progressWindowSeconds: 2,
};

type DistanceSample = {time: number; distanceM: number};
export type GoalState = {
  config: GoalConfig;
  targetM: Vec3;
  initialDistanceM: number;
  initialRootComM: Vec3;
  initialTime: number;
  lastTime: number;
  previousDistanceM: number;
  maxProgressM: number;
  holdSeconds: number;
  qualifying: boolean;
  fallen: boolean;
  history: readonly DistanceSample[];
};

export type GoalMetrics = {
  rootComM: Vec3;
  initialDistanceM: number;
  distanceM: number;
  /** Signed net closing. Returning to the baseline removes all net progress. */
  progressM: number;
  /** Signed step difference; summing it telescopes, so rocking cannot farm reward. */
  deltaProgressM: number;
  maxProgressM: number;
  progressFraction: number;
  /** Progress retained throughout the trailing window; zero until the window fills. */
  sustainedProgressM: number;
  recentClosingSpeedMps: number;
  progressWindowReady: boolean;
  centerStandOffM: readonly [number, number];
  /** Envelope estimate, not a mesh-distance/contact query. */
  frontGapM: number;
  headingErrorRad: number;
  tiltRad: number;
  nearTarget: boolean;
  madeProgress: boolean;
  headingAligned: boolean;
  upright: boolean;
  fallen: boolean;
  holdSeconds: number;
  success: boolean;
  elapsedSeconds: number;
  state: GoalState;
};

const clamp = (x: number, lo: number, hi: number) => Math.max(lo, Math.min(hi, x));
const wrap = (x: number) => Math.atan2(Math.sin(x), Math.cos(x));
const EPS = 1e-9;
function finite(x: number, label: string): void {
  if (!Number.isFinite(x)) throw Error(`${label} must be finite`);
}
function vector(v: Vec3, label: string): void {
  if (v.length !== 3 || v.some(x => !Number.isFinite(x))) throw Error(`Invalid ${label}`);
}
function rotation(q: Quat): void {
  if (q.length !== 4 || q.some(x => !Number.isFinite(x)) || Math.abs(Math.hypot(...q) - 1) > 1e-3)
    throw Error('Body quaternion must be finite and unit length');
}
function rotate(q: Quat, p: Vec3): Vec3 {
  const [x, y, z, w] = q;
  const tx = 2 * (y * p[2] - z * p[1]);
  const ty = 2 * (z * p[0] - x * p[2]);
  const tz = 2 * (x * p[1] - y * p[0]);
  return [p[0] + w * tx + y * tz - z * ty,
    p[1] + w * ty + z * tx - x * tz, p[2] + w * tz + x * ty - y * tx];
}
function measure(frame: GoalFrame, target: Vec3, config: GoalConfig) {
  finite(frame.time, 'frame.time');
  vector(frame.links.body.position, 'body position');
  rotation(frame.links.body.quaternion);
  const offset = rotate(frame.links.body.quaternion, config.rootLocalComM);
  const position = frame.links.body.position;
  const rootComM: Vec3 = [position[0] + offset[0], position[1] + offset[1], position[2] + offset[2]];
  const dx = target[0] - rootComM[0], dy = target[1] - rootComM[1];
  const forward = rotate(frame.links.body.quaternion, [1, 0, 0]);
  const up = rotate(frame.links.body.quaternion, [0, 0, 1]);
  return {rootComM, distanceM: Math.hypot(dx, dy),
    headingErrorRad: wrap(Math.atan2(dy, dx) - Math.atan2(forward[1], forward[0])),
    tiltRad: Math.acos(clamp(up[2], -1, 1))};
}
function validateConfig(config: GoalConfig): void {
  vector(config.rootLocalComM, 'rootLocalComM');
  for (const [key, value] of Object.entries(config)) {
    if (key === 'rootLocalComM') continue;
    if (typeof value !== 'number' || !Number.isFinite(value) || value <= 0)
      throw Error(`${key} must be finite and positive`);
  }
  if (config.minFrontGapM >= config.maxFrontGapM || config.maxHeadingErrorRad >= Math.PI / 2 ||
      config.maxUprightTiltRad >= Math.PI * .31)
    throw Error('Invalid success geometry or orientation thresholds');
}

/** Capture once after settling. Reset it whenever the target or physics episode changes. */
export function createGoalState(frame: GoalFrame, target: Vec3,
  options: Pick<GoalConfig, 'rootLocalComM'> & Partial<Omit<GoalConfig, 'rootLocalComM'>>): GoalState {
  vector(target, 'target');
  const config = {...GOAL_DEFAULTS, ...options, rootLocalComM: [...options.rootLocalComM] as Vec3};
  validateConfig(config);
  const initial = measure(frame, target, config);
  return {config, targetM: [...target], initialDistanceM: initial.distanceM,
    initialRootComM: initial.rootComM, initialTime: frame.time, lastTime: frame.time,
    previousDistanceM: initial.distanceM, maxProgressM: 0, holdSeconds: 0, qualifying: false,
    fallen: frame.metrics.fall || initial.tiltRad > Math.PI * .31 || frame.links.body.position[2] < .019,
    history: [{time: frame.time, distanceM: initial.distanceM}]};
}

/** Pure update: retain result.state. dt is elapsed simulation time, never wall-clock time.
 * Repeated timestamps add neither dwell nor reward. Invalid data/changed baselines throw.
 * The fixed environment target belongs here; image size/neck pose are deliberately absent.
 */
export function goalMetrics(frame: GoalFrame, target: Vec3, initialDistanceM: number,
  dt: number, state: GoalState): GoalMetrics {
  vector(target, 'target'); finite(initialDistanceM, 'initialDistanceM'); finite(dt, 'dt');
  if (dt < 0 || dt > 1) throw Error('dt must be between zero and one simulation second');
  if (target.some((x, i) => Math.abs(x - state.targetM[i]) > EPS) ||
      Math.abs(initialDistanceM - state.initialDistanceM) > EPS)
    throw Error('Target and baseline are fixed for an episode; create a new goal state after reset');
  const measured = measure(frame, target, state.config);
  const advance = frame.time - state.lastTime;
  // Rapier advances in 1/300 s quanta; tolerate one quantum when the caller uses 1/60 s.
  if (advance < -EPS || advance > dt + 1 / 300 + EPS)
    throw Error('Frame time must advance monotonically with the supplied simulation dt');
  if (advance <= EPS && Math.abs(measured.distanceM - state.previousDistanceM) > EPS)
    throw Error('A changed pose requires an advancing simulation timestamp');
  const config = state.config;
  const baseExtent = config.robotFrontExtentM + config.targetHalfWidthM;
  const centerStandOffM = [baseExtent + config.minFrontGapM, baseExtent + config.maxFrontGapM] as const;
  const progressM = initialDistanceM - measured.distanceM;
  const deltaProgressM = state.previousDistanceM - measured.distanceM;
  const fallen = state.fallen || frame.metrics.fall || measured.tiltRad > Math.PI * .31 ||
    frame.links.body.position[2] < .019;
  const nearTarget = measured.distanceM >= centerStandOffM[0] - EPS &&
    measured.distanceM <= centerStandOffM[1] + EPS;
  const madeProgress = progressM >= config.minProgressM - EPS;
  const headingAligned = Math.abs(measured.headingErrorRad) <= config.maxHeadingErrorRad;
  const upright = !fallen && measured.tiltRad <= config.maxUprightTiltRad;
  const qualifies = nearTarget && madeProgress && headingAligned && upright;
  // Count only intervals whose two sampled endpoints meet every requirement.
  const holdSeconds = qualifies && state.qualifying ? state.holdSeconds + Math.max(0, advance) : 0;
  const history = state.history.map(sample => ({...sample}));
  if (advance > EPS) history.push({time: frame.time, distanceM: measured.distanceM});
  const cutoff = frame.time - config.progressWindowSeconds;
  // Retain an interpolated sample at the exact trailing-window boundary.
  while (history.length > 1 && history[1].time <= cutoff) history.shift();
  if (history.length > 1 && history[0].time < cutoff) {
    const a = history[0], b = history[1];
    const fraction = (cutoff - a.time) / (b.time - a.time);
    history[0] = {time: cutoff, distanceM: a.distanceM + fraction * (b.distanceM - a.distanceM)};
  }
  const elapsedSeconds = frame.time - state.initialTime;
  const progressWindowReady = elapsedSeconds >= config.progressWindowSeconds - EPS;
  const sustainedProgressM = progressWindowReady ? Math.max(0,
    initialDistanceM - Math.max(...history.map(sample => sample.distanceM))) : 0;
  const windowSeconds = frame.time - history[0].time;
  const recentClosingSpeedMps = windowSeconds > EPS ?
    (history[0].distanceM - measured.distanceM) / windowSeconds : 0;
  const maxProgressM = Math.max(state.maxProgressM, progressM);
  const requiredClosingM = initialDistanceM - centerStandOffM[1];
  const next: GoalState = {...state, lastTime: frame.time, previousDistanceM: measured.distanceM,
    maxProgressM, holdSeconds, qualifying: qualifies, fallen, history};
  return {...measured, initialDistanceM, progressM, deltaProgressM, maxProgressM,
    progressFraction: requiredClosingM > EPS ? clamp(progressM / requiredClosingM, 0, 1) : 0,
    sustainedProgressM, recentClosingSpeedMps, progressWindowReady, centerStandOffM,
    frontGapM: measured.distanceM - baseExtent, nearTarget, madeProgress, headingAligned,
    upright, fallen, holdSeconds, success: qualifies && holdSeconds >= config.holdSeconds - EPS,
    elapsedSeconds, state: next};
}

/** Candidate episode score based on physical closing, never apparent image area.
 * The worker should separately reject trials without adequate image observation coverage.
 * Signed net progress punishes retreat; retained progress favors gains surviving the window.
 */
export function goalScore(metrics: Pick<GoalMetrics,
  'fallen' | 'progressM' | 'sustainedProgressM' | 'success'>): number {
  if (metrics.fallen) return -6;
  finite(metrics.progressM, 'progressM'); finite(metrics.sustainedProgressM, 'sustainedProgressM');
  return 40 * metrics.progressM + 80 * metrics.sustainedProgressM + (metrics.success ? 10 : 0);
}
