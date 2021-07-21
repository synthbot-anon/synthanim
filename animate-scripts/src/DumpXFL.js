import synthrunner from 'common/synthrunner.js'
import { getRootLayers, SymbolExporter } from 'common/AnimationTree.js';


const sourceFile = "%sourceFile";
const outputFile = "%outputFile";

synthrunner((logger) => {
	fl.closeAll()
	document = fl.openDocument(`file:///${sourceFile}`);
	const output = fl.getDocumentDOM().saveAsCopy(`file:///${outputFile}.xfl`);
	fl.closeDocument(document, false);	
});