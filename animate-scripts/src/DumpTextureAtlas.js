import synthrunner from 'common/synthrunner.js'
import { getRootLayers, SymbolExporter } from 'common/AnimationTree.js';


// Array of { sourceFile: [{symbolName, destFolder}] }
const assetFile = JSON.parse("%symbols");

synthrunner((logger) => {
	fl.closeAll()
	document = fl.openDocument(`file:///${assetFile.sourceFile}`);

	const rootLayers = getRootLayers();
	const exporter = new SymbolExporter();

	rootLayers.map((rootLayer) => {
		exporter.addSequences(rootLayer.getSequences());
	});

	assetFile.samples.forEach((sample) => {
		exporter.dumpTextureAtlas(sample.symbolName, `file:///${sample.destFolder}`);
		// exporter.dumpFramesForSymbol(symName);
	})

	fl.closeDocument(document, false)
});
