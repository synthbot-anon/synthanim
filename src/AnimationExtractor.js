import 'common/polyfill.js';
import logger from 'common/synthlogger.js'
import { getRootLayers, SymbolExporter } from 'common/AnimationTree.js';

logger.trace("--- ---");
fl.showIdleMessage(false);

// const allLayers = getRootLayers();
// const appendDescendants = (layer) => {
// 	layer.getChildren().forEach((x) => {
// 		allLayers.push(x);
// 		logger.trace(x.name, x.startFrame, x.duration);
// 		appendDescendants(x);
// 	});
// }

// getRootLayers().forEach((x) => appendDescendants(x));

const rootLayers = getRootLayers();
const exporter = new SymbolExporter("C:/Users/synthbot/animation_dump");

rootLayers.map((rootLayer) => {
	exporter.addSequences(rootLayer.getSequences());
});

exporter.dumpAllSymbolSamples();

// const rootSequences = rootLayers.map((x) => {
// 	exporter.addSequences(x.getSequences());
// });

// logger.trace(exporter.getAllSymbolNames().join("\n"));

// const twilightSymbol = exporter.getSymbolsByName("EAR")[0];
// exporter.dumpSymbolSpritesheet(twilightSymbol);

logger.trace("done");
