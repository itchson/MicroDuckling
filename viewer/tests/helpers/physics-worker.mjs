// Run the actual browser worker protocol in Node without a DOM or WebGL substitute.
import {parentPort} from 'node:worker_threads';
globalThis.onmessage=undefined;
globalThis.postMessage=value=>parentPort.postMessage(value);
await import('../../lib/simulation.worker.ts');
parentPort.on('message',data=>globalThis.onmessage({data}));
