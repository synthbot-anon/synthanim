import synthrunner from 'common/synthrunner.js'
import { getAnimationFile, SymbolExporter } from 'common/AnimationTree.js';


const sourceFile = "%sourceFile";

synthrunner((logger) => {
	document = fl.openDocument(`file:///${sourceFile}`);
	document.currentTimeline = 0;

	const animationFile = getAnimationFile();
	const exporter = new SymbolExporter();
	exporter.addAnimationFile(animationFile);
	exporter.debug();

	// fl.closeDocument(document, false);
});
