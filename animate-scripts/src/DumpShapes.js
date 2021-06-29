import synthrunner from 'common/synthrunner.js'
import { getAnimationFile, SymbolExporter } from 'common/AnimationTree.js';


const sourceFile = "%sourceFile";
const outputDir = "%outputDir";

	// .fastForwardUntil("MLP922_175A.fla")
synthrunner((logger) => {
	// fl.closeAll()
	// document = fl.openDocument(`file:///${sourceFile}`);

	const animationFile = getAnimationFile();
	const exporter = new SymbolExporter();
	exporter.addAnimationFile(animationFile);

	// const sourceFileParts = sourceFile.split("/");
	// const sourceFileName = sourceFileParts[sourceFileParts.length - 1];

	exporter.dumpShapeSpritesheet(); //sourceFileName, outputDir);
	// fl.closeDocument(document, false);
});
		
// font problem: MLP922_147.fla