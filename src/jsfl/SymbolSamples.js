import 'common/polyfill.js';
import synthrunner from 'common/synthrunner.js'
import { getRootLayers, SymbolExporter } from 'common/AnimationTree.js';
import SynthFileConverter from 'common/SynthFileConverter.js';

logger.tee("C:/Users/synthbot/Desktop/animate_logs2.txt");
logger.trace("--- ---");
fl.showIdleMessage(false);

const clipperDir = "C:/Users/synthbot/Desktop/Sorted Animation Assets/1 - FLA/6 - Scenes";
const outputDir = "C:/Users/synthbot/animation_dump/6 - test";

const isPathSeparator = (char) => {
	return char === "/" || char === "\\";
}

const relpath = (fullPath, rootPath) => {
	const trimmedPath = fullPath.trim();
	const trimmedRoot = rootPath.trim();

	const result = trimmedPath.substring(trimmedRoot.length, trimmedPath.length);
	return result.substring(
		(isPathSeparator(result[0])) ? 1 : 0,
		result.length
	);
}

const catpath = (rootPath, relPath) => {
	return rootPath + "/" + relPath;
}

new SynthFileConverter()
	// .fastForwardUntil("MLP922_175A.fla")
	.limit(1)
	.registerFLAs(clipperDir)
	.forEachFLA((sourceFile) => {
		try {
			logger.trace("converting", relpath(sourceFile, clipperDir));
			const destFile = catpath(outputDir, relpath(sourceFile, clipperDir))

			document = fl.openDocument(`file:///${sourceFile}`);
			const rootLayers = getRootLayers();
			const exporter = new SymbolExporter();

			rootLayers.map((rootLayer) => {
				exporter.addSequences(rootLayer.getSequences());
			});

			exporter.dumpAllSymbolSamples(destFile);

		} catch(err) {
			logger.trace("failed to convert", flaPath);
			logger.trace("...", err);
		}

		fl.closeDocument(document, false);
	})

// font problem: MLP922_147.fla



fl.closeAll(true);
logger.trace("done");
