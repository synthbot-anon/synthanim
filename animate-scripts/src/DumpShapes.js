import synthrunner from 'common/synthrunner.js'
import { getAnimationFile, SymbolExporter } from 'common/AnimationTree.js';


const sourceFile = "%sourceFile";
const outputDir = "%outputDir";

	// .fastForwardUntil("MLP922_175A.fla")
synthrunner((logger) => {
	const document = fl.openDocument(`file:///${sourceFile}`);
	const exporter = new SymbolExporter();
	exporter.dumpShapeSpritesheet(`${outputDir}`);

	fl.closeDocument(document, false);
});
