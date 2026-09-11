// SPDX-License-Identifier: Apache-2.0
import assert from 'node:assert/strict';
import {asset,BrowserPhysics,CAMERA_WADDLE_GAIT,RockingTrainer,compactEpisode,hash,save} from './common.mjs';
const engine=await BrowserPhysics.create(asset),episodes=[],generations=[];
const startWall=performance.now();
try {
  const trainer=new RockingTrainer(engine,{seed:2026,population:12,elite:3,episodeSeconds:14,seedGait:CAMERA_WADDLE_GAIT,
    onEpisode:(result,candidateIndex)=>episodes.push({ordinal:episodes.length+1,candidateIndex,
      gaitSha256:hash(JSON.stringify(result.gait)),...compactEpisode(result)})});
  let result;
  for(let n=0;n<8;n++) {
    result=trainer.stepGeneration();
    assert.equal(result.episodesEvaluated,2+(n+1)*12);
    assert.equal(episodes.length,result.episodesEvaluated);
    assert.equal(result.candidates.length,12);
    assert.ok(Math.abs(result.scoreImprovementOverSeed-(result.best.score-result.seed.score))<1e-10);
    assert.ok(Math.abs(result.improvementOverSeedM-(result.best.distanceM-result.seed.distanceM))<1e-10);
    const independentlyImproved=result.bestOrigin==='search'&&!result.best.fall&&result.best.score>result.seed.score+.1&&
      result.best.lateForwardSpeedMps>result.seed.lateForwardSpeedMps+.0001;
    assert.equal(result.improvedOverSeed,independentlyImproved);
    generations.push({generation:result.generation,episodesEvaluated:result.episodesEvaluated,bestOrigin:result.bestOrigin,
      bestScore:result.best.score,bestDistanceM:result.best.distanceM,bestLateForwardSpeedMps:result.best.lateForwardSpeedMps,
      improvedOverSeed:result.improvedOverSeed,scoreImprovementOverSeed:result.scoreImprovementOverSeed,
      improvementOverSeedM:result.improvementOverSeedM,generationMeanScore:result.meanScore,
      fallCount:result.candidates.filter(c=>c.fall).length});
    console.log(JSON.stringify(generations.at(-1)));
  }
  assert.equal(episodes.length,98);
  assert.equal(episodes.filter(e=>e.candidateIndex===-2).length,1);
  assert.equal(episodes.filter(e=>e.candidateIndex===-1).length,1);
  assert.equal(episodes.filter(e=>e.candidateIndex>=0).length,96);
  const winningHash=hash(JSON.stringify(result.best.gait));
  assert.ok(episodes.some(e=>e.gaitSha256===winningHash&&Math.abs(e.score-result.best.score)<1e-10));
  await save('training-results.json',{experiment:'canonical RockingTrainer final asset accounting',seed:2026,
    generationsRequested:8,population:12,elite:3,episodeSeconds:14,physicsOptions:engine.options,
    rawEpisodeCallbackCount:episodes.length,neutralBaselineCount:1,providedSeedCount:1,candidateEvaluationCount:96,
    generationCountsVerified:true,reportedImprovementVerified:true,winningCandidateActuallyEvaluated:true,
    finalBestOrigin:result.bestOrigin,improvedOverSeed:result.improvedOverSeed,
    scoreImprovementOverSeed:result.scoreImprovementOverSeed,improvementOverSeedM:result.improvementOverSeedM,
    neutralBaseline:compactEpisode(result.baseline),providedSeed:compactEpisode(result.seed),best:compactEpisode(result.best),
    bestGait:result.bestGait,bestGaitSha256:winningHash,wallSeconds:(performance.now()-startWall)/1000,generations,episodes});
  console.log(JSON.stringify({finished:true,rawEpisodeCount:episodes.length,improvedOverSeed:result.improvedOverSeed,bestOrigin:result.bestOrigin}));
} finally {engine.dispose();}
