import 'common/polyfill.js';
import synthrunner from 'common/synthrunner.js'
import { getRootLayers, SymbolExporter } from 'common/AnimationTree.js';
import SynthFileConverter from 'common/SynthFileConverter.js';

// read list of symbols to dump
// get full list of available fla files
// for each fla file
// ... get list of relevant symbols
// ... dump the symbol


logger.tee("C:/Users/synthbot/Desktop/symdump_logs.txt");
logger.trace("--- ---");
fl.showIdleMessage(false);

const clipperDir = "C:/Users/synthbot/Desktop/Sorted Animation Assets/1 - FLA/6 - Scenes";
const labelDir = "C:/Users/synthbot/Desktop/symbol-labels";
const outputDir = "C:/Users/synthbot/animation_dump/full-symbols";

new SynthFileConverter()
	.registerLabels(labelDir)
	.registerFLAs(clipperDir)
	.fastForwardUntil("MLP624_265")
	.limit(2)
	.forEachFLA((flaPath, forEachSym) => {
		logger.trace("opening", flaPath);
		document = fl.openDocument(`file:///${flaPath}`);

		const rootLayers = getRootLayers();
		const exporter = new SymbolExporter();

		rootLayers.map((rootLayer) => {
			exporter.addSequences(rootLayer.getSequences());
		});

		forEachSym(({ symName, charName }) => {
			logger.trace("charname:", charName);
			logger.trace("symid:", symName);
			exporter.dumpTextureAtlas(symName, `file:///C:/Users/synthbot/vt`);
			exporter.dumpFramesForSymbol(symName);
		});
	})


// fl.closeAll(true);
// convertDirectory(clipperDir, outputDir);

logger.trace("done");
