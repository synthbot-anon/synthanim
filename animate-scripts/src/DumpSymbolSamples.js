import synthrunner from 'common/synthrunner.js'
import { getRootLayers, SymbolExporter } from 'common/AnimationTree.js';


const sourceFile = "%sourceFile";
const outputDir = "%outputDir";

	// .fastForwardUntil("MLP922_175A.fla")
synthrunner((logger) => {
	fl.closeAll()
	document = fl.openDocument(`file:///${sourceFile}`);

	const rootLayers = getRootLayers();
	const exporter = new SymbolExporter();
	rootLayers.map((rootLayer) => {
		exporter.addSequences(rootLayer.getSequences());
	});

	const sourceFileParts = sourceFile.split("/");
	const sourceFileName = sourceFileParts[sourceFileParts.length - 1];

	exporter.dumpAllSymbolSamples(sourceFileName, outputDir);
	fl.closeDocument(document, false);
});
		
// font problem: MLP922_147.fla