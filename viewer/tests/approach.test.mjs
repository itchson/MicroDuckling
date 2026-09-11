import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {BrowserPhysics} from '../lib/browser-physics.ts';
import {ApproachEpisode} from '../lib/approach.ts';
import {CAMERA_WADDLE_GAIT} from '../lib/locomotion-controller.ts';
import {detectTarget,DEFAULT_VISION_PARAMETERS} from '../lib/vision.ts';
import {CpuCamera,WIDTH,HEIGHT,FOV} from '../scripts/cpu-camera.mjs';
const asset=JSON.parse(readFileSync(new URL('../../simulation/browser/robot-physics.json',import.meta.url)));

test('actual CAD camera drives stable physical approach ahead, left and right across reset seeds',async()=>{
  const engine=await BrowserPhysics.create(asset),camera=new CpuCamera(asset);
  try{
    for(const y of [0,.04,-.04])for(const seed of [2026,42]){
      const target=[.18,y,.05],episode=new ApproachEpisode(engine,asset,CAMERA_WADDLE_GAIT,DEFAULT_VISION_PARAMETERS,target,{seed,seconds:30});
      let result=episode.current();
      while(!result.finished){
        const pixels=camera.capture(result.frame,target),observation=detectTarget(pixels,WIDTH,HEIGHT,FOV*Math.PI/180);
        result=episode.observe(observation,result.frame.time);
      }
      assert.equal(result.goal.success,true,`targetY=${y}, seed=${seed}: ${JSON.stringify(result.goal)}`);
      assert.equal(result.goal.fallen,false);assert.ok(result.goal.progressM>=.025);assert.ok(result.goal.holdSeconds>=1.5-1e-7);
      assert.equal(result.eligible,true);assert.ok(result.visibleFraction>.5);assert.ok(result.goal.distanceM>=.11&&result.goal.distanceM<=.13);
    }
  }finally{engine.dispose();camera.dispose();}
});

test('missing or mismatched camera frames cannot advance approach or create success',async()=>{
  const engine=await BrowserPhysics.create(asset);
  try{
    const episode=new ApproachEpisode(engine,asset,CAMERA_WADDLE_GAIT,DEFAULT_VISION_PARAMETERS,[.18,0,.05],{seconds:2});
    const before=episode.current();assert.equal(before.goal.success,false);assert.equal(before.observations,0);
    assert.throws(()=>episode.observe({visible:true,bearingRad:0,areaFraction:1,widthFraction:1},before.frame.time-.1));
    assert.equal(engine.frame().time,before.frame.time);
    let result=before;
    while(!result.finished)result=episode.observe({visible:true,bearingRad:0,areaFraction:1,widthFraction:1},result.frame.time);
    assert.equal(result.goal.success,false,'Filling the image while standing still is not an approach');
    assert.ok(Math.abs(result.goal.progressM)<.005);assert.ok(result.score<1);
  }finally{engine.dispose();}
});
