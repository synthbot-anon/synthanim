import synthrunner from 'common/synthrunner.js'
import { getAnimationFile, SymbolExporter } from 'common/AnimationTree.js';


const sourceFile = "%sourceFile";
const shapes = JSON.parse("%shapes");
const outputDir = "%outputDir";

	// .fastForwardUntil("MLP922_175A.fla")
synthrunner((logger) => {
	document = fl.openDocument(`file:///${sourceFile}`);
	document.currentTimeline = 0;

	const animationFile = getAnimationFile();
	const exporter = new SymbolExporter();
	exporter.addAnimationFile(animationFile);

	exporter.dumpShapeSpritesheet(`${outputDir}/spritemaps`);

	fl.closeDocument(document, false);
});
