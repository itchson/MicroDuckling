// SPDX-License-Identifier: Apache-2.0
import test from 'node:test';
import assert from 'node:assert/strict';
import {createGoalState, goalMetrics, goalScore} from '../lib/goal-metrics.ts';

const target = [.24, 0, .05];
const options = {rootLocalComM: [0, 0, 0]};
const yaw = a => [0, 0, Math.sin(a / 2), Math.cos(a / 2)];
const pitch = a => [0, Math.sin(a / 2), 0, Math.cos(a / 2)];
function frame(time, x = 0, y = 0, quaternion = [0, 0, 0, 1], fall = false, z = .055) {
  return {time, links: {body: {position: [x, y, z], quaternion}}, metrics: {fall}};
}
function initial(f = frame(0), t = target, config = options) {return createGoalState(f, t, config);}
function step(state, f, t = target) {
  return goalMetrics(f, t, state.initialDistanceM, f.time - state.lastTime, state);
}
function hold(state, x, seconds, {y = 0, quaternion = [0, 0, 0, 1], fall = false} = {}) {
  let result;
  for (let n = 0; n < Math.round(seconds * 20); n++) {
    result = step(state, frame(state.lastTime + .05, x, y, quaternion, fall));
    state = result.state;
  }
  return result;
}
function close(actual, expected, tolerance = 1e-9) {assert.ok(Math.abs(actual - expected) < tolerance, `${actual} != ${expected}`);}

test('measures horizontal range to fixed target, not absolute world +X displacement', () => {
  const t = [0, .24, 5], state = initial(frame(0), t);
  const result = step(state, frame(.1, 0, .03, yaw(Math.PI / 2)), t);
  close(result.distanceM, .21); close(result.progressM, .03);
  close(result.headingErrorRad, 0);
});

test('transforms body local COM and never silently substitutes its origin', () => {
  const f = frame(0, .1, .2, yaw(Math.PI / 2));
  const state = initial(f, [.1, .44, .05], {rootLocalComM: [.01, 0, .02]});
  close(state.initialRootComM[0], .1); close(state.initialRootComM[1], .21);
  close(state.initialRootComM[2], .075); close(state.initialDistanceM, .23);
});

test('head motion and arbitrary camera diagnostics cannot generate progress or success', () => {
  let state = initial();
  for (let n = 1; n <= 80; n++) {
    const f = {...frame(n * .05), cameraArea: n / 80, neckYaw: n / 20};
    const result = step(state, f); state = result.state;
    close(result.progressM, 0); close(goalScore(result), 0); assert.equal(result.success, false);
  }
});

test('requires 25 mm of closing even when initially in the stand-off band', () => {
  const state = initial(frame(0, .12));
  const result = hold(state, .12, 4);
  assert.equal(result.nearTarget, true); assert.equal(result.madeProgress, false);
  assert.equal(result.success, false); close(result.holdSeconds, 0);
});

test('60 mm robot front +25 mm target half-width yields110–130 mm center stand-off', () => {
  const result = step(initial(), frame(.1, .12));
  close(result.frontGapM, .035);
  close(result.centerStandOffM[0], .11); close(result.centerStandOffM[1], .13);
  assert.equal(result.nearTarget, true);
  assert.equal(step(initial(), frame(.1, .131)).nearTarget, false); // 109 mm: too close
  assert.equal(step(initial(), frame(.1, .109)).nearTarget, false); // 131 mm: too far
});

test('requires continuous1.5 s dwell and does not credit time before entering the band', () => {
  const entered = step(initial(), frame(.5, .12));
  close(entered.holdSeconds, 0); assert.equal(entered.success, false);
  const short = hold(entered.state, .12, 1.45);
  assert.equal(short.success, false);
  const done = step(short.state, frame(short.state.lastTime + .05, .12));
  assert.equal(done.success, true); close(done.holdSeconds, 1.5);
});

test('heading uses body direction, so a turned head cannot hide a sideways body', () => {
  const result = hold(initial(), .12, 3, {quaternion: yaw(Math.PI / 2)});
  assert.equal(result.nearTarget, true); assert.equal(result.headingAligned, false);
  assert.equal(result.success, false);
});

test('bearing wraps correctly around the negative-X axis', () => {
  const t = [-.24, -.001, .05];
  const state = initial(frame(0, 0, 0, yaw(Math.PI - .01)), t);
  const result = step(state, frame(.1, -.12, 0, yaw(Math.PI - .01)), t);
  assert.ok(Math.abs(result.headingErrorRad) < .02);
});

test('heading, tilt, range or retreat interruption resets dwell', () => {
  for (const interruption of [
    frame(1.1, .12, 0, yaw(.5)),
    frame(1.1, .12, 0, pitch(.3)),
    frame(1.1, .10),
  ]) {
    const prior = hold(initial(), .12, 1);
    assert.ok(prior.holdSeconds > .8);
    const interrupted = step(prior.state, interruption);
    close(interrupted.holdSeconds, 0); assert.equal(interrupted.success, false);
    const restarted = hold(interrupted.state, .12, 1);
    assert.equal(restarted.success, false);
  }
});

test('fall flag is latched even if a later frame appears recovered', () => {
  const fallen = step(initial(), frame(.1, .12, 0, [0, 0, 0, 1], true));
  const recovered = hold(fallen.state, .12, 3);
  assert.equal(recovered.fallen, true); assert.equal(recovered.success, false);
  assert.equal(goalScore(recovered), -6);
});

test('physical collapse or extreme tilt rejects an incorrectly false fall flag', () => {
  for (const bad of [frame(.1, .12, 0, pitch(1.1)), frame(.1, .12, 0, [0, 0, 0, 1], false, .018)]) {
    const result = step(initial(), bad);
    assert.equal(result.fallen, true); assert.equal(result.success, false);
  }
});

test('fall after apparent success revokes success if worker has not terminated yet', () => {
  const completed = hold(initial(), .12, 2);
  assert.equal(completed.success, true);
  const fallen = step(completed.state, frame(completed.state.lastTime + .05, .12, 0, [0, 0, 0, 1], true));
  assert.equal(fallen.success, false);
});

test('signed delta reward telescopes and retreat removes transient advance', () => {
  let state = initial(), sum = 0, result;
  for (const [time, x] of [[.1, .04], [.2, .01], [.3, -.02], [.4, 0]]) {
    result = step(state, frame(time, x)); state = result.state; sum += result.deltaProgressM;
  }
  close(sum, 0); close(result.progressM, 0); close(goalScore(result), 0);
  close(result.maxProgressM, .04); // Diagnostic peak is intentionally excluded from score.
});

test('sustained progress is zero before a full window, then uses its worst retained distance', () => {
  const early = hold(initial(), .04, 1);
  close(early.sustainedProgressM, 0); assert.equal(early.progressWindowReady, false);
  const retained = hold(early.state, .04, 2);
  close(retained.sustainedProgressM, .04); assert.equal(retained.progressWindowReady, true);
  const retreat = step(retained.state, frame(retained.state.lastTime + .05, .01));
  close(retreat.sustainedProgressM, .01);
  assert.ok(goalScore(retreat) < goalScore(retained));
});

test('late-window speed distinguishes real sustained travel from initial settling', () => {
  let state = initial(), result;
  for (let n = 1; n <= 200; n++) {
    result = step(state, frame(n * .05, n * .05 * .001)); state = result.state;
  }
  close(result.recentClosingSpeedMps, .001);
  const settled = hold(state, .01, 3);
  close(settled.recentClosingSpeedMps, 0);
});

test('duplicate frames do not accumulate dwell, and helper leaves prior state untouched', () => {
  const entered = step(initial(), frame(.1, .12));
  const state = entered.state, snapshot = JSON.stringify(state);
  for (let n = 0; n < 100; n++) {
    const result = goalMetrics(frame(.1, .12), target, state.initialDistanceM, .05, state);
    close(result.holdSeconds, 0); assert.equal(result.success, false);
  }
  assert.equal(JSON.stringify(state), snapshot);
});

test('reset target or initial distance cannot manufacture closing; invalid clocks are rejected', () => {
  const state = initial();
  assert.throws(() => goalMetrics(frame(.1), [.12, 0, .05], .24, .1, state), /fixed/);
  assert.throws(() => goalMetrics(frame(.1), target, .50, .1, state), /fixed/);
  assert.throws(() => goalMetrics(frame(2), target, .24, .1, state), /monotonically/);
  assert.throws(() => goalMetrics(frame(-.1), target, .24, .1, state), /monotonically/);
  assert.throws(() => goalMetrics(frame(0, .12), target, .24, 0, state), /advancing/);
  assert.throws(() => goalMetrics(frame(.1), target, .24, NaN, state), /finite/);
});

test('malformed positions/quaternions fail closed rather than produce success', () => {
  assert.throws(() => step(initial(), frame(.1, NaN)), /position/);
  assert.throws(() => step(initial(), frame(.1, .12, 0, [0, 0, 0, 0])), /quaternion/);
  assert.throws(() => initial(frame(0), target, {...options, minProgressM: 0}), /positive/);
});
