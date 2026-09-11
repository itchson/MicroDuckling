// SPDX-License-Identifier: Apache-2.0
// Read-only reproduction of the worker's camera search, using its shared episode.
import {readFileSync, writeFileSync, mkdirSync} from 'node:fs';
import {createHash} from 'node:crypto';
import {BrowserPhysics} from '../../lib/browser-physics.ts';
import {ApproachEpisode} from '../../lib/approach.ts';
import {CAMERA_WADDLE_GAIT} from '../../lib/locomotion-controller.ts';
import {detectTarget, DEFAULT_VISION_PARAMETERS, proposeVisionParameters} from '../../lib/vision.ts';
import {GOAL_DEFAULTS} from '../../lib/goal-metrics.ts';
import {CpuCamera, WIDTH, HEIGHT, FOV} from '../cpu-camera.mjs';

const root = new URL('../../../', import.meta.url);
mkdirSync(new URL('work/',root),{recursive:true});
const read = path => readFileSync(new URL(path, root));
const sha = data => createHash('sha256').update(data).digest('hex');
const hash = path => sha(read(path));
const expectedAsset = process.env.EXPECTED_ASSET_SHA256;
if (expectedAsset && hash('simulation/browser/robot-physics.json') !== expectedAsset) throw Error('Unexpected canonical physics asset');
const asset = JSON.parse(read('simulation/browser/robot-physics.json'));
const assembly = JSON.parse(read('cad/assembly.json'));
const components = JSON.parse(read('components/records.json'));
const cached = JSON.parse(read('viewer/public/cad/assembly.json'));
const expectedParts = [...assembly.parts, ...components.parts].filter(p => p.kind !== 'coupon');
const cameraParts = cached.parts.filter(p => p.kind !== 'coupon');
if (JSON.stringify(cameraParts.map(p => [p.name, p.link])) !== JSON.stringify(expectedParts.map(p => [p.name, p.link])))
  throw Error('Reference camera cache differs from canonical part/link list');
const sourcePaths = [
  'simulation/browser/robot-physics.json', 'cad/assembly.json', 'components/records.json',
  'viewer/public/cad/assembly.json', 'viewer/lib/browser-physics.ts', 'viewer/lib/approach.ts',
  'viewer/lib/goal-metrics.ts', 'viewer/lib/goal-types.ts', 'viewer/lib/vision.ts',
  'viewer/lib/experiment-settings.ts',
  'viewer/lib/locomotion-controller.ts', 'viewer/lib/simulation.worker.ts',
  'viewer/lib/simulation-protocol.ts', 'viewer/scripts/cpu-camera.mjs',
  'viewer/scripts/prepare-cad.mjs', 'viewer/package-lock.json', 'viewer/scripts/verification/camera-learning.mjs',
];
const sourceHashes = Object.fromEntries(sourcePaths.map(p => [p, hash(p)]));
const geometryInputs = cameraParts.map(p => {
  const canonical = `${components.parts.some(c => c.name === p.name) ? 'components' : 'cad'}/meshes/${p.name}.json`;
  const cache = `viewer/public/cad/meshes/${p.name}.json`;
  const value = hash(canonical);
  if (hash(cache) !== value) throw Error(`Stale camera mesh: ${p.name}`);
  return {canonical, cache, sha256: value};
});
const settings = {groundFriction: .7, footFriction: .9, bodyFriction: .35, massScale: 1};
const output = {
  schemaVersion: 1,
  startedAtUtc: new Date().toISOString(),
  verificationScope: 'Shared ApproachEpisode and worker candidate/selection logic with 96x72 CAD-occluded CPU reference camera. No WebGL browser rendering, worker transport, or physical hardware verification in this run.',
  sourceHashes,
  cameraGeometry: {assembledParts: cameraParts.length, canonicalCacheHashesMatch: true,
    digestMethod: 'SHA256 of JSON array of canonical relative path and file SHA256, in camera part order',
    sha256: sha(JSON.stringify(geometryInputs.map(p => [p.canonical, p.sha256])))},
  runtime: {node: process.version, rapier: '0.20.0'},
  configuration: {settings, fixedDt: 1 / 600, solverIterations: 16, soleCollider: 'convex',
    width: WIDTH, height: HEIGHT, verticalFovDegrees: FOV, imagePeriodSeconds: .1,
    commandPeriodSeconds: 1 / 60, trialSeconds: 60, trainSeed: 2026,
    trainTargetM: [.18, .04, .05], targetHalfExtentsM: [.025, .025, .05],
    gait: structuredClone(CAMERA_WADDLE_GAIT), goal: GOAL_DEFAULTS,
    initialParameters: {...DEFAULT_VISION_PARAMETERS},
    selectionRule: 'candidate = proposeVisionParameters(currentBest, zeroBasedTrial); retain iff eligible && (bestScore is null || score > bestScore)',
    scoreRule: 'fallen ? -6 : 40 * progressM + 80 * sustainedProgressM + (success ? 10 : 0)'},
  trials: [], heldOut: [], completed: false,
};
const save = () => writeFileSync(new URL('work/camera-learning.json', root), JSON.stringify(output, null, 2) + '\n');
const engine = await BrowserPhysics.create(asset, settings);
const camera = new CpuCamera(asset);
output.physics = engine.diagnostics();
const summarize = result => ({
  score: result.score, eligible: result.eligible, success: result.goal.success, fallen: result.goal.fallen,
  progressM: result.goal.progressM, sustainedProgressM: result.goal.sustainedProgressM,
  distanceM: result.goal.distanceM, initialDistanceM: result.goal.initialDistanceM,
  headingErrorRad: result.goal.headingErrorRad, tiltRad: result.goal.tiltRad,
  holdSeconds: result.goal.holdSeconds, elapsedSeconds: result.goal.elapsedSeconds,
  observations: result.observations, visibleFraction: result.visibleFraction, coverageFraction: result.coverageFraction,
});
function evaluate(parameters, target, seed) {
  const started = performance.now();
  const episode = new ApproachEpisode(engine, asset, CAMERA_WADDLE_GAIT, parameters, target, {seed, seconds: 60});
  let result = episode.current();
  while (!result.finished) {
    const pixels = camera.capture(result.frame, target);
    const observation = detectTarget(pixels, WIDTH, HEIGHT, FOV * Math.PI / 180);
    result = episode.observe(observation, result.frame.time);
  }
  return {...summarize(result), wallSeconds: (performance.now() - started) / 1000};
}
try {
  let best = {...DEFAULT_VISION_PARAMETERS}, bestScore = null, selectedTrial = null;
  for (let trial = 0; trial < 12; trial++) {
    const parameters = proposeVisionParameters(best, trial);
    const result = evaluate(parameters, output.configuration.trainTargetM, 2026);
    const retained = result.eligible && (bestScore === null || result.score > bestScore);
    if (retained) {best = {...parameters}; bestScore = result.score; selectedTrial = trial;}
    output.trials.push({trial, parameters, ...result, retained, bestScoreAfter: bestScore});
    output.selectedParameters = best; output.selectedTrial = selectedTrial; output.bestScore = bestScore;
    save(); console.log(JSON.stringify({phase: 'training', trial, ...result, retained}));
  }
  for (const seed of [42, 99]) for (const y of [-.04, 0, .04]) {
    const targetM = [.18, y, .05];
    const result = evaluate(best, targetM, seed);
    output.heldOut.push({seed, targetM, ...result});
    save(); console.log(JSON.stringify({phase: 'heldOut', seed, targetM, ...result}));
  }
  const changed = sourcePaths.filter(p => hash(p) !== sourceHashes[p]);
  for (const input of geometryInputs) for (const p of [input.canonical, input.cache])
    if (hash(p) !== input.sha256) changed.push(p);
  if (changed.length) throw Error(`Inputs changed during evaluation: ${changed.join(', ')}`);
  output.inputsUnchanged = true;
  output.completed = true; output.finishedAtUtc = new Date().toISOString();
  output.summary = {trainingSuccesses: output.trials.filter(t => t.success).length,
    trainingEligible: output.trials.filter(t => t.eligible).length,
    scoreImprovementOverInitial: bestScore - output.trials[0].score,
    heldOutSuccesses: output.heldOut.filter(t => t.success).length,
    heldOutEligible: output.heldOut.filter(t => t.eligible).length,
    heldOutFalls: output.heldOut.filter(t => t.fallen).length};
  save(); console.log(JSON.stringify({phase: 'complete', ...output.summary, selectedTrial, selectedParameters: best}));
} catch (error) {
  output.error = String(error); save(); throw error;
} finally {camera.dispose(); engine.dispose();}
