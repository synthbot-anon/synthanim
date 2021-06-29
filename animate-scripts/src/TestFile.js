import synthrunner from 'common/synthrunner.js'
import { getRootLayers, SymbolExporter } from 'common/AnimationTree.js';


const sourceFile = "%sourceFile";

synthrunner((logger) => {
	document = fl.openDocument(`file:///${sourceFile}`);
	fl.closeDocument(document, false);	
});