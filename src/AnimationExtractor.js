import 'common/polyfill.js';
import logger from 'common/synthlogger.js'
import { getRootLayers, SymbolExporter } from 'common/AnimationTree.js';

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
const exporter = new SymbolExporter("C:/Users/synthbot/animation_dump");

const rootSequences = rootLayers.map((x) => {
	exporter.addSequences(x.getSequences());
});

const twilightSymbol = exporter.getSymbolsByName("TS")[0];
exporter.dumpSymbolSpritesheet(twilightSymbol);

logger.trace("done");

// allLayers.forEach((x) => {
// 	logger.trace(x.name, x.startFrame, x.duration);
// })
