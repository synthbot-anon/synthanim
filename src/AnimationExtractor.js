import 'common/polyfill.js';
import logger from 'common/synthlogger.js'
import { getRootLayers, SymbolExporter } from 'common/AnimationTree.js';

logger.trace("--- ---");
fl.showIdleMessage(false);

const clipperDir = "C:/Users/synthbot/Desktop/Sorted Animation Assets/1 - FLA/6 - Scenes";
const outputDir = "C:/Users/synthbot/animation_dump/6 - Scenes";

const g = {
	// to resume processing, skip all files by filename before this one
	fastforwardUntil: "MLP214_043.fla",
};

const convertCurrentDocument = (destFile) => {
	const rootLayers = getRootLayers();
	const exporter = new SymbolExporter();

	rootLayers.map((rootLayer) => {
		exporter.addSequences(rootLayer.getSequences());
	});

	exporter.dumpAllSymbolSamples(destFile);
}

const convertDirectory = (sourceDir, destinationDir) => {
	const availableFiles = FLfile.listFolder(`file:///${sourceDir}`, "files");
	FLfile.createFolder(destinationDir);

	for (let filename of availableFiles) {
		if (g.fastforwardUntil) {
			if (filename != g.fastforwardUntil) {
				continue;
			}
			
			g.fastforwardUntil = false;
		}

		const filenameLower = filename.toLowerCase();
		if (!filename.endsWith(".fla")) {
			continue;
		}

		const sourceFile = `${sourceDir}/${filename}`;
		const destinationFile = `${destinationDir}/${filename}`;

		logger.trace("creating", destinationFile);

		fl.openDocument(`file:///${sourceFile}`);
		convertCurrentDocument(destinationFile);
		fl.closeAll(false);
	}

	const availableDirectories = FLfile.listFolder(`file:///${sourceDir}`, "directories");
	for (let dirname of availableDirectories) {
		const newSourceDir = `${sourceDir}/${dirname}`;
		const newdestinationDir = `${destinationDir}/${dirname}`;
		convertDirectory(newSourceDir, newdestinationDir);
	}
}

fl.closeAll(true);
convertDirectory(clipperDir, outputDir);

logger.trace("done");
