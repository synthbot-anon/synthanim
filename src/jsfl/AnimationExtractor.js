import 'common/polyfill.js';
import synthrunner from 'common/synthrunner.js'
import { getRootLayers, SymbolExporter } from 'common/AnimationTree.js';

logger.tee("C:/Users/synthbot/Desktop/animate_logs.txt");
logger.trace("--- ---");
fl.showIdleMessage(false);

const clipperDir = "C:/Users/synthbot/Desktop/Sorted Animation Assets/1 - FLA/6 - Scenes";
const outputDir = "C:/Users/synthbot/animation_dump/6 - Scenes";

const g = {
	// to resume processing, skip all files by filename before this one
	fastforwardUntil: "MLP922_067B_2019-01-21_09-41-16.fla",
};

const convertDocument = (sourceFile, destFile) => {
	document = fl.openDocument(`file:///${sourceFile}`);
	const rootLayers = getRootLayers();
	const exporter = new SymbolExporter();

	rootLayers.map((rootLayer) => {
		exporter.addSequences(rootLayer.getSequences());
	});

	exporter.dumpAllSymbolSamples(destFile);
	fl.closeDocument(document, false);
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

		try {
			logger.trace("creating", destinationFile);
			convertDocument(sourceFile, destinationFile);
		} catch(err) {
			logger.trace("failed to convert", sourceFile);
		}
		
		
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
