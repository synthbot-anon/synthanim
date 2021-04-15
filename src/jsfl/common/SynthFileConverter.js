class NestedMaps {
	constructor() {
		this.knownMaps = {};
	}

	set(value, key, ...rest) {
		if (rest.length === 0) {
			this.knownMaps[key] = value;
		} else {
			let subMap = this.knownMaps[key];
			if (!subMap) {
				subMap = new NestedMaps();
				subMap.set(value, ...rest)
				this.knownMaps[key] = subMap;
			}
		}
	}

	get(key, ...rest) {
		if (rest.length === 0) {
			return this.knownMaps[key];
		} else {
			return this.knownMaps[key].get(...rest);
		}
	}
}


// const g = {
	// to resume processing, skip all files by filename before this one
	// fastforwardUntil: "MLP922_175A.fla",
	// labels: new NestedMaps(),
	// flaFiles: {},
	// iter: 0,
// };

class SynthFileConverter {
	constructor() {
		this.firstFile = false;
		this.labels = new NestedMaps();
		this.flaFiles = {};
		this.iter = 0;
		this.maxFiles = false;
	}

	fastForwardUntil(filename) {
		this.firstFile = filename;
		return this;
	}

	limit(n) {
		this.maxFiles = n;
		return this;
	}

	registerLabels(labelDir) {
		getFilesRecursively(labelDir)
			.slice(2000, 2100)
			.map((labelFilename) => {
				const flaName = labelFileToFLA(labelFilename);
				const symName = labelFileToSym(labelFilename);
				const charName = labelFileToCharacter(labelFilename);
				this.labels.set(charName, flaName, symName);
			});

		return this;
	}

	registerFLAs(flaDir) {
		getFilesRecursively(flaDir)
			.map((flaFilepath) => {
				const match = /([^/\\]*)\.fla$/i.match(flaFilepath);
				if (!match) {
					logger.trace("skipping file", flaFilepath);
					return;
				}

				const flaName = match[1];
				this.iter += 1;
				if (this.iter < 100) {
					logger.trace(flaName, ":", flaFilepath);
				}
				this.flaFiles[flaName] = flaFilepath.replaceAll('\\\\', '/');
			});

		return this;
	}

	forEachFLA(flaFn) {
		logger.trace("iterating over flas");
		for (let flaName of Object.keys(this.flaFiles)) {
			logger.trace("iteration:", flaName);
			if (this.firstFile) {
				if (flaName != this.firstFile) {
					logger.trace("skipping", flaName);
					continue;
				}
				this.firstFile = false;
			}

			const flaPath = this.flaFiles[flaName];
			const symbols = this.labels.get(flaName);

			let forEachSym;
			logger.trace("flaName:", flaName);
			logger.trace("symbols:", symbols);
			if (symbols) {
				forEachSym = (symFn) => {
					for (let symName of Object.keys(symbols.knownMaps)) {
						const charName = symbols.get(symName);
						symFn({ symName, charName })
					}
				};
			}

			flaFn(flaPath, forEachSym);

			if (this.maxFiles) {
				if (this.maxFiles === 1) {
					break;
				}
				this.maxFiles -= 1;
			}

			// fl.closeDocument(document, false);
		}
	}
}

export default SynthFileConverter;

// font problem: MLP922_147.fla

const getFilesRecursively = (folder) => {
	const result = [];
	const remainingFolders = [`file:///${folder}`];

	while (remainingFolders.length !== 0) {
		const currentFolder = remainingFolders.pop();
		logger.trace("checking", currentFolder);
		for (let nextFolder of FLfile.listFolder(currentFolder, "directories")) {
			remainingFolders.push(`${currentFolder}/${nextFolder}`);
		}

		for (let discoveredFile of FLfile.listFolder(currentFolder, "files")) {
			result.push(FLfile.uriToPlatformPath(`${currentFolder}/${discoveredFile}`));
		}
	}

	return result;
}

const labelFileToFLA = (labelFilename) => {
	const explicitFla = /f-(.*)\.fla/i.match(labelFilename);
	const implicitFla = /(.*)\.fla/i.match(labelFilename);
	return explicitFla[1] || implicitFla.group[1];
}

const labelFileToSym = (labelFilename) => {
	const explicitSym = /s-(.*)_f[0-9]{0,4}\.sym/i.match(labelFilename);
	const implicitSym = /(.*)_f[0-9]{0,4}\.png/i.match(labelFilename);
	return explicitSym[1] || implicitSym[1];
}

const labelFileToCharacter = (labelFilename) => {
	const fslashSplit = labelFilename.split("\\");
	return fslashSplit[fslashSplit.length - 2];
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
			logger.trace("...", err);
		}
	}

	const availableDirectories = FLfile.listFolder(`file:///${sourceDir}`, "directories");
	for (let dirname of availableDirectories) {
		const newSourceDir = `${sourceDir}/${dirname}`;
		const newdestinationDir = `${destinationDir}/${dirname}`;
		convertDirectory(newSourceDir, newdestinationDir);
	}
}