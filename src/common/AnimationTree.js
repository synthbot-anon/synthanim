import logger from 'common/synthlogger.js';

export const getRootLayers = () => {
	const timeline = fl.getDocumentDOM().getTimeline();
	const file = new AnimationFile();
	return timeline.layers.map((x) => new AnimationLayer(file, x));
};

class AnimationFile {
	constructor() {
		this.knownSymbols = {};
	}

	getSymbolFromElement(flElement) {
		const symbolId = flElement.guid;
		if (symbolId in this.knownSymbols) {
			return this.knownSymbols[symbolId];
		}

		const result = new AnimationSymbol(this, symbolId, flElement);
		this.knownSymbols[symbolId] = result;
		return result;
	}
}

class AnimationSymbol {
	constructor(file, symbolId, flElement) {
		this.file = file;
		this.id = symbolId;
		this.flElement = flElement;
		this.flSymbol = flElement.libraryItem;
		this.timeline = flElement.libraryItem.timeline;
		this.names = {};
	}

	attachName(name) {
		this.names[name] = true;
	}

	getNames() {
		return Object.keys(this.names).join(",");
	}

	getLayers() {
		return this.timeline.layers.map((x) => new AnimationLayer(this.file, x));
	}
}

class SymbolFrame {
	constructor(symbol, frameIndex, flFrame) {
		this.symbol = symbol;
		this.frameIndex = frameIndex;
		this.flFrame = flFrame;
	}

	allSymbolFrames() {
		const result = [];
		const pending = [this];

		while (pending.length !== 0) {
			const currentSymbolFrame = pending.pop();
			result.push(currentSymbolFrame);
			currentSymbolFrame.symbol.getLayers().forEach((childLayer) => {
				const layerFrames = childLayer.getSymbolFrames(currentSymbolFrame.frameIndex);
				if (layerFrames === null) {
					currentSymbolFrame.hasInvalidFrames = true;
				} else {
					currentSymbolFrame.hasInvalidFrames = false;
					pending.push(...layerFrames);
				}
			});
		}

		return result;
	}
}

class AnimationSequence {
	constructor(symbol) {
		this.symbol = symbol;
		this.frames = [];
	}

	pushFrame(frame) {
		this.frames.push(frame);
	}

}

class SequenceGenerator {
	constructor() {
		this.completedSequences = [];
		this.touchedSequences = {};
		this.openSequences = {};
	}

	placeSymbolFrame(symbolFrame) {
		const symbol = symbolFrame.symbol;
		let sequence;

		if (symbol.id in this.openSequences) {
			sequence = this.openSequences[symbol.id];
		} else {
			sequence = new AnimationSequence(symbol);
			this.openSequences[symbol.id] = sequence;
		}

		this.touchedSequences[symbol.id] = true;
		sequence.pushFrame(symbolFrame);
	}

	nextFrame() {
		for (let prevOpenSymbol in this.openSequences) {
			if (!(prevOpenSymbol in this.touchedSequences)) {
				// broke the sequence, so whatever was there is complete
				const prevOpenSeq = this.openSequences[prevOpenSymbol];
				this.completedSequences.push(prevOpenSeq);
				delete this.openSequences[prevOpenSymbol];
			}
		}

		this.touchedSequences = {};
	}

	getSequences() {
		this.nextFrame();
		this.nextFrame();
		return this.completedSequences;
	}
}

class AnimationLayer {
	constructor(file, flLayer) {
		this.file = file;
		this.flLayer = flLayer;
		this.name = flLayer.name;
	}

	getSequences() {
		const generator = new SequenceGenerator();

		for (let frameIndex=0; frameIndex<this.flLayer.frames.length; frameIndex++) {
			this.getSymbolFrames(frameIndex).forEach((symbolFrame) => {
				symbolFrame.symbol.attachName(this.name);
				generator.placeSymbolFrame(symbolFrame);	
			});

			generator.nextFrame();
		}

		return generator.getSequences();
	}

	getSymbolFrames(frameIndex) {
		const result = [];
		const flFrame = this.flLayer.frames[frameIndex];

		if (!flFrame) {
			logger.trace("invalid frame index", frameIndex, "for layer", this.name);
			return null;
		}

		// logger.trace("getting frames:", frameIndex, "of", this.flLayer.frames.length, "for", this.name);
		
		for (let flElement of flFrame.elements) {
			if (!elementHasFrames(flElement)) {
				continue;
			}

			const symbol = this.file.getSymbolFromElement(flElement);
			symbol.attachName(this.name);

			const symbolDisplayIndex = getSymbolDisplayIndex(flFrame, frameIndex, flElement);
			const symbolFrame = new SymbolFrame(symbol, symbolDisplayIndex, flFrame);

			result.push(symbolFrame);
		}

		return result;
	}
}

const elementHasFrames = (flElement) => {
	if (!('symbolType' in flElement)) {
		return false;
	}

	if (flElement.symbolType === "movie clip") {
		return false;
	}

	return true;
}

const getSymbolDisplayIndex = (flFrame, frameIndex, flElement) => {
	const symbolFrameIter = frameIndex - flFrame.startFrame;
	const symbolLastFrame = (
		(flElement.lastFrame === -1)
			? flElement.libraryItem.timeline.frameCount
			: flElement.lastFrame);
	let symbolDisplayIndex;

	if (flElement.loop === "single frame") {
		symbolDisplayIndex = flElement.firstFrame;
	} else if (flElement.loop === "play once") {
		symbolDisplayIndex = Math.floor(
			flElement.firstFrame + symbolFrameIter, symbolLastFrame-1);
	} else if (flElement.loop === "loop") {
		symbolDisplayIndex = flElement.firstFrame + (
			symbolFrameIter % (symbolLastFrame - flElement.firstFrame));
	} else {
		logger.trace("unknown loop type:", flElement.loop, "in", );
		logger.trace("elementType:", flElement.elementType);
		logger.trace("instanceType:", flElement.instanceType);
		logger.trace("symbolType:", flElement.symbolType);
		logger.trace("effectSymbol:", flElement.effectSymbol);
		logger.traceProperties(flElement);
	}

	return symbolDisplayIndex;

}

class ArrayMaps {
	constructor() {
		this.knownMaps = {};
	}

	set(arrayId, arrayIndex, value) {
		let knownMap = this.knownMaps[arrayId];
		if (!knownMap) {
			knownMap = [];
			this.knownMaps[arrayId] = knownMap;
		}

		knownMap[arrayIndex] = value;
	}

	push(arrayId, value) {
		const offset = (this.get(arrayId) || []).length
		this.set(arrayId, offset, value);
	}

	get(arrayId, arrayIndex) {
		const arrayResult = this.knownMaps[arrayId];
		if (arrayIndex !== undefined) {
			return arrayResult[arrayIndex];
		}

		return arrayResult;
	}

	compactKeys() {
		const result = [];

	}
}

export class SymbolExporter {
	constructor(folderPath) {
		this.rootPath = folderPath;
		this.sequences = [];
		this.framesBySymbolId = new ArrayMaps();
		this.symbolsById = {};
	}

	addSequences(sequences) {
		sequences.forEach((seq) => {
			seq.frames.map((sequenceFrame) => {
				for (let componentFrame of sequenceFrame.allSymbolFrames()) {
					this.symbolsById[componentFrame.symbol.id] = componentFrame.symbol;
					this.framesBySymbolId.set(
						componentFrame.symbol.id, componentFrame.frameIndex, true
					);
				}
			});
		});
	}

	getSymbolsByName(name) {
		const result = [];

		for (let id in this.symbolsById) {
			const symbol = this.symbolsById[id];
			if (name in symbol.names) {
				result.push(symbol);
			}
		}

		return result;
	}

	getMedianFrame(symbol) {
		const frames = Object.keys(this.framesBySymbolId.get(symbol.id));
		frames.sort();

		const offset = Math.floor(frames.length / 2);
		return parseInt(frames[offset]);
	}

	dumpSymbolSpritesheet(symbol) {
		const frameIndex = this.getMedianFrame(symbol);
		const exporter = new SpriteSheetExporter();
		const spritePath = `file:///${this.rootPath}/${symbol.id}.png`;
		symbol.flSymbol.exportToPNGSequence(spritePath, frameIndex+1, frameIndex+1);

		const framePath = getFrameFilename(spritePath, frameIndex+2);
		FLfile.remove(framePath);
	}
}

const getFrameFilename = (uri, frameIndex) => {
	const parts = uri.split(".");
	const extension = parts.pop();
	return `${parts.join(".")}${frameIndex.toString().padStart(4, 0)}.${extension}`;
}