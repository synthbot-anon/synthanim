import 'common/polyfill.js';
import logger from 'common/synthlogger.js'
import { getRootLayers } from 'common/AnimationTree.js';

const greet = (name) => {
	logger.trace("hello", name);
};

logger.tee("~/log.txt");
greet("blackcat"); 

const allLayers = getRootLayers();
const appendDescendants = (layer) => {
	layer.getChildren().forEach((x) => {
		allLayers.push(x);
		logger.trace(x.name, x.startFrame, x.duration);
		appendDescendants(x);
	});
}

// getRootLayers().forEach((x) => appendDescendants(x));

const rootLayers = getRootLayers();
const scene = rootLayers.filter((x) => x.name === "SCENE")[0];
const rootSequences = rootLayers.map((x) => x.getSequences());

rootLayers.forEach((layer) => {
	const sequences = layer.getSequences();

	sequences.forEach((sequence) => {
		// logger.trace("symbol:", sequence.symbol.id, sequence.symbol.flElement.guid, sequence.symbol.getNames());
		logger.trace(layer.name, "frames:", ...sequence.frames.map((x) => {
			const symbolFrames = x.allSymbolFrames();
			return [symbolFrames.length, x.hasInvalidFrames];
		}));
	});
});


// allLayers.forEach((x) => {
// 	logger.trace(x.name, x.startFrame, x.duration);
// })
