import { logger } from "common/synthrunner.js";
import ImagePacker from 'common/ImagePacker.js';

export const getAnimationFile = () => {
	return new AnimationFile(fl.getDocumentDOM());
};


const toValidFilename = (proposal) => {
	return (proposal.replaceAll('_', '__')
			.replaceAll('\\*', '_s')
			.replaceAll('\\/', '_f')
			.replaceAll('\\\\', '_b')
			.replaceAll('~', '_t')
			.replaceAll(':', '_c')
			.replaceAll('"', '_q')
			.replaceAll('<', '_l')
			.replaceAll('>', '_r')
			.replaceAll('\\|', '_p')
			.replaceAll('\\?', '_m'));
}

const fromValidFilename = (filename) => {
	return (filename.replaceAll('_m', '?')
		.replaceAll('_p', '|')
		.replaceAll('_r', '>')
		.replaceAll('_l', '<')
		.replaceAll('_q', '"')
		.replaceAll('_c', ':')
		.replaceAll('_t', '~')
		.replaceAll('_b', '\\')
		.replaceAll('_f', '/')
		.replaceAll('_s', '*')
		.replaceAll('__', '_'));
}

class AnimationFile {
	constructor(document) {
		this.flDocument = document;
		this.rootTimeline = document.getTimeline();
		this.knownSymbols = {};
		this.symbolIdFromGuid = {};
		this.knownShapes = {};
		this.shapeIdFromGuid = {};
		this.knownMovies = {};
		this.movieIdFromGuid = {};
		this.knownLayers = {};
		this.rootLayers = this.rootTimeline.layers.map((x, i) => {
			const layerId = `L${i}`;
			const result = new AnimationLayer(this, null, layerId, x, i);
			this.knownLayers[layerId] = result;
			return result;
		});

		this.sceneStack = [];
		this.visitingAncestors = {};
	}

	getSymbolId(proposal, guid) {
		if (guid in this.symbolIdFromGuid) {
			return this.symbolIdFromGuid[guid];
		}

		this.symbolIdFromGuid[guid] = proposal;
		return proposal;
	}

	getShapeId(proposal, guid) {
		if (guid in this.shapeIdFromGuid) {
			return this.shapeIdFromGuid[guid];
		}

		this.shapeIdFromGuid[guid] = proposal;
		return proposal;	
	}

	getMovieId(proposal, guid) {
		if (guid in this.movieIdFromGuid) {
			return this.movieIdFromGuid[guid];
		}

		this.movieIdFromGuid[guid] = proposal;
		return proposal;
	}

	enterElement(animationElement, fn) {
		const commonAncestor = null;
		const currentElementToAncestor = [];

		let currentElement = animationElement;
		while (currentElement && !commonAncestor) {
			if (currentElement.id in this.visitingAncestors) {
				commonAncestor = currentElement;
				break;
			}	

			currentElementToAncestor.push(currentElement);
			currentElement = currentElement.layer.symbol;
		}

		// go up to the common ancestor
		while (this.sceneStack.length) {
			if (this.sceneStack[this.sceneStack.length - 1] === commonAncestor) {
				break;
			}

			this.flDocument.exitEditMode();
			const removedElement = this.sceneStack.pop();
			delete this.visitingAncestors[removedElement.id];
		}

		// go down to the next shape
		while (currentElementToAncestor.length) {
			const nextElement = currentElementToAncestor.pop();
			fn(nextElement)

			nextElement.refreshFlObjects();
			nextElement.select();

			// nextElement.layer.flLayer.locked = false;
			// nextElement.layer.flLayer.visible = true;
			// this.flDocument.getTimeline().currentFrame = nextElement.frameIndex;
			// this.flDocument.selectNone();			
			// nextElement.flElement.selected = true;
			// this.flDocument.selection = [nextElement.flElement];
			// this.flDocument.livePreview = true;


			this.flDocument.enterEditMode("inPlace");
			this.sceneStack.push(nextElement);
			this.visitingAncestors[nextElement.id] = nextElement;
		}
	}

	selectElement(animationElement, fn) {
		const parent = animationElement.layer.symbol;
		this.enterElement(parent, fn);
		
		fn(animationElement)
		animationElement.refreshFlObjects();
		animationElement.select();
		// const shapeTimeline = this.flDocument.getTimeline();
		// const shapeLayer = shapeTimeline.layers[animationElement.layer.layerIndex];
		// const shapeFrame = shapeLayer.frames[animationElement.frameIndex];
		// const flShape = shapeFrame.elements[animationElement.elementIndex];

		// shapeTimeline.currentFrame = animationElement.frameIndex;
		// shapeLayer.locked = false;
		// shapeLayer.visible = true;
		// flShape.selected = true
		// this.flDocument.selection = [flShape];
		// this.flDocument.livePreview = true;
	}

	getSceneElement() {
		return this.sceneStack[this.sceneStack.length-1];
	}
}

class AnimationElement {
	constructor(file, layer, frameIndex, id, flElement, elementIndex) {
		this.file = file;
		this.layer = layer;
		this.frameIndex = frameIndex;
		this.id = id;
		this.elementIndex = elementIndex;
		this.flElement = flElement;

		this.flTimeline = null;
		this.flLayer = null;
		this.flFrame = null;

	}

	refreshFlObjects(doc) {
		// MUST be in the parent symbol's edit mode before calling this
		this.flTimeline = (doc || this.file.flDocument).getTimeline();
		this.flLayer = this.flTimeline.layers[this.layer.layerIndex];
		this.flFrame = this.flLayer.frames[this.frameIndex];

		if (this.flElement.elementType === 'shape') {
			// I don't understand this. It seems necessary for shape elements,
			// but doing it for symbols breaks Animate's ability to find them.
			this.flElement = this.flFrame.elements[this.elementIndex];	
		}
	}

	select(doc) {
		(doc || this.file.flDocument).getTimeline().currentFrame = this.frameIndex;
		this.layer.flLayer.locked = false;
		this.layer.flLayer.visible = true;
		this.layer.flLayer.layerType = "normal";
		this.file.flDocument.livePreview = true;
		(doc || this.file.flDocument).selectNone();
		this.flElement.selected = true
		// this.file.flDocument.selection = [this.flElement];
		// this.file.flDocument.livePreview = true;
		// if (!this.flElement.selected) {
		// 	logger.log("failed to select element!");
		// 	throw Error("wtf");
		// }
		// if (this.file.flDocument.selection[0] !== this.flElement) {
		// 	logger.log("failed to select element!");
		// 	throw Error("wtf");
		// }
	}
}

class AnimationShape extends AnimationElement {
	constructor(file, layer, frameIndex, shapeId, flElement, elementIndex) {
		super(file, layer, frameIndex, shapeId, flElement, elementIndex);
		this.transformX = flElement.transformX;
		this.transformY = flElement.transformY;
	}
}

class AnimationMovie extends AnimationElement {
	constructor(file, layer, frameIndex, movieId, flElement, elementIndex) {
		super(file, layer, frameIndex, movieId, flElement, elementIndex);
	}
}

class AnimationSymbol extends AnimationElement {
	constructor(file, layer, frameIndex, symbolId, flElement, elementIndex) {
		super(file, layer, frameIndex, symbolId, flElement, elementIndex);
		this.flSymbol = flElement.libraryItem;
		this.timeline = flElement.libraryItem.timeline;
		this.names = {};
		this.frames = [];
		this.movieClip = elementIsMovieClip(flElement);
	}

	attachName(name) {
		this.names[name] = true;
	}

	getNames() {
		return Object.keys(this.names).join(",");
	}

	getLayerFromFlLayer(layerIndex, flLayer) {
		const layerId = `${this.id}_L${layerIndex}`;
		if (layerId in this.file.knownLayers) {
			return this.file.knownLayers[layerId];
		}

		const result = new AnimationLayer(this.file, this, layerId, flLayer, layerIndex);
		result.movieClip = this.movieClip;
		this.file.knownLayers[layerId] = result;
		return result;
	}

	getLayers() {
		return this.timeline.layers.map((x, i) => this.getLayerFromFlLayer(i, x));
	}

	registerFrame(symbolFrame) {
		this.frames[symbolFrame.frameIndex] = symbolFrame;
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

			inSymbol1 = false;
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
	constructor(file, symbol, layerId, flLayer, layerIndex) {
		this.file = file;
		this.symbol = symbol;
		this.id = layerId;
		this.flLayer = flLayer;
		this.name = flLayer.name;
		this.layerIndex = layerIndex;
		this.movieClip = false;
	}

	getSymbolFromFlElement(frameIndex, elementIndex, flElement) {
		const symbolIdProposal = flElement.libraryItem.name;
		const symbolId = this.file.getSymbolId(symbolIdProposal, flElement.guid);

		if (symbolId in this.file.knownSymbols) {
			return this.file.knownSymbols[symbolId];
		}

		const result = new AnimationSymbol(this.file, this, frameIndex, symbolId, flElement, elementIndex);
		this.file.knownSymbols[symbolId] = result;
		return result;
	}

	getShapeFromFlElement(frameIndex, elementIndex, flElement) {
		const shapeIdProposal = `${this.id}_F${frameIndex}_E${elementIndex}`;
		const shapeId = this.file.getShapeId(shapeIdProposal, flElement.guid);

		if (shapeId in this.file.knownShapes) {
			return this.file.knownShapes[shapeId];
		}

		const result = new AnimationShape(this.file, this, frameIndex, shapeId, flElement, elementIndex);
		this.file.knownShapes[shapeId] = result;
		return result;
	}

	getMovieFlElement(frameIndex, elementIndex, flElement) {
		const movieIdProposal = `${this.id}_F${frameIndex}_M${elementIndex}`;
		const movieId = this.file.getMovieId(movieIdProposal, flElement.guid);

		if (movieId in this.file.knownMovies) {
			return this.file.knownMovies[movieId];
		}

		const result = new AnimationMovie(this.file, this, frameIndex, movieId, flElement, elementIndex);
		this.file.knownMovies[movieId] = result;
		return result;
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
		const flFrame = (this.movieClip)
			? this.flLayer.frames[0]
			: this.flLayer.frames[frameIndex];

		if (!flFrame) {
			// logger.log("invalid frame index", frameIndex, "for layer", this.name);
			return null;
		}

		flFrame.elements.forEach((flElement, elementIndex) => {
			if (elementIsExternal(flElement)) {
				return;
			}

			if (!elementHasFrames(flElement)) {
				this.getShapeFromFlElement(frameIndex, elementIndex, flElement);
				return;
			}

			const symbol = this.getSymbolFromFlElement(frameIndex, elementIndex, flElement);
			symbol.attachName(this.name);

			const symbolDisplayIndex = this.getSymbolDisplayIndex(flFrame, frameIndex, flElement);
			const symbolFrame = new SymbolFrame(symbol, symbolDisplayIndex, flFrame);
			symbol.registerFrame(symbolFrame);

			result.push(symbolFrame);
		});
			
		return result;
	}

	getSymbolDisplayIndex = (flFrame, frameIndex, flElement) => {
		const symbolFrameIter = frameIndex - flFrame.startFrame;

		const symbolLastFrame = (
			(flElement.lastFrame === -1)
				? flElement.libraryItem.timeline.frameCount
				: flElement.lastFrame);
		let symbolDisplayIndex;

		if (this.movieClip) {
			const loopSize = flElement.libraryItem.timeline.frameCount
			const firstFrame = (!flElement.firstFrame)
				? 0
				: flElement.firstFrame;

			symbolDisplayIndex = firstFrame + (
				symbolFrameIter % loopSize);
		} else if (flElement.loop === "loop") {
			const loopSize = symbolLastFrame - flElement.firstFrame;
			symbolDisplayIndex = flElement.firstFrame + (
				symbolFrameIter % loopSize);
		} else if (flElement.loop === "single frame" || !flElement.loop) {
			symbolDisplayIndex = (!flElement.firstFrame)
				? 0
				: flElement.firstFrame;
		} else if (flElement.loop === "play once") {
			symbolDisplayIndex = Math.floor(
				flElement.firstFrame + symbolFrameIter, symbolLastFrame-1);
		} else {
			logger.log("unknown loop type:", flElement.loop, "in", );
			logger.log("elementType:", flElement.elementType);
			logger.log("instanceType:", flElement.instanceType);
			logger.log("symbolType:", flElement.symbolType);
			logger.log("effectSymbol:", flElement.effectSymbol);
			logger.logProperties(flElement);
		}

		return symbolDisplayIndex;

	}
}

const elementIsExternal = (flElement) => {
	if (flElement.elementType !== "instance") {
		return false;
	}

	if (flElement.instanceType === "symbol") {
		return false;
	}

	return true;
}

const elementHasFrames = (flElement) => {
	// TODO: check if this can be replaced with elementType === "instance"
	// return (flElement.elementType === "instance");

	if ('instanceType' in flElement) {
		if (flElement.instanceType === "symbol") {
			return true;
		}
	}

	if (!('symbolType' in flElement)) {
		return false;
	}

	return true;
}

const elementIsMovieClip = (flElement) => {
	if (flElement.elementType !== "instance") {
		return false;
	}

	if (flElement.instanceType !== "symbol") {
		return false;
	}

	if (flElement.symbolType !== "movie clip") {
		return false;
	}

	return true;
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

	getCompact(arrayId) {
		const result = [];
		const keys = Object.keys(this.knownMaps[arrayId]);

		if (keys.length === 0) {
			return result;
		}

		let nextBatch = null;
		for (let nextKey of keys) {
			if (nextBatch && (nextKey-1 === nextBatch[nextBatch.length-1])) {
				nextBatch.push(nextKey)
			} else {
				if (nextBatch) {
					result.push(nextBatch);
				}
				nextBatch = [nextKey];
			}
		}

		return result;
	}
}

export class SymbolExporter {
	constructor() {
		this.animationFile = null;
		this.sequences = [];
		this.framesBySymbolId = new ArrayMaps();
		this.symbolsById = {};
		this.sequencesBySymbolId = {};
	}

	addAnimationFile(animationFile) {
		this.animationFile = animationFile;

		animationFile.rootLayers.forEach((rootLayer) => {
			const sequences = rootLayer.getSequences();
			const generator = new SequenceGenerator();

			sequences.forEach((seq) => {
				seq.frames.map((sequenceFrame) => {
					for (let componentFrame of sequenceFrame.allSymbolFrames()) {
						generator.placeSymbolFrame(componentFrame);
						this.symbolsById[componentFrame.symbol.id] = componentFrame.symbol;
						this.framesBySymbolId.set(
							componentFrame.symbol.id, componentFrame.frameIndex, true
						);
					}
				});
			});

			generator.getSequences().forEach((seq) => {
				const knownSequences = this.sequencesBySymbolId[seq.symbol.id] || [];
				knownSequences.push(seq.frames);
				this.sequencesBySymbolId[seq.symbol.id] = knownSequences;
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

	getAllSymbolNames() {
		const result = [];

		for (let id in this.symbolsById) {
			const symbol = this.symbolsById[id];
			result.push(...Object.keys(symbol.names));
		}

		return result;
	}

	getMedianFrame(symbol) {
		const frames = Object.keys(this.framesBySymbolId.get(symbol.id));
		frames.sort();

		const offset = Math.floor(frames.length / 2);
		return parseInt(frames[offset]);
	}

	dumpSymbolSample(sourceFileName, symbol, folder) {
		const frameIndex = this.getMedianFrame(symbol);
		const exporter = new SpriteSheetExporter();
		const spriteFilename = toValidFilename(symbol.id);
		const spritePath = `file:///${folder}/f-${sourceFileName}_s-${spriteFilename}.sym_f.png`;

		try {
			symbol.flSymbol.exportToPNGSequence(spritePath, frameIndex+1, frameIndex+1);
		} catch(err) {
			logger.log("failed to convert item: ", symbol.id);
		}

		const framePath = getFrameFilename(spritePath, frameIndex+2);
		FLfile.remove(framePath);
	}

	dumpAllSymbolSamples(sourceFileName, folder) {
		FLfile.createFolder(`file:///${folder}`);
		for (let symbolId in this.symbolsById) {
			const symbol = this.symbolsById[symbolId];
			this.dumpSymbolSample(sourceFileName, symbol, folder);
		}
	}

	dumpTextureAtlas(fileSafeSymbolId, folder) {
		const symbolId = fromValidFilename(fileSafeSymbolId);
		logger.log("symbol:", symbolId);
		const rootSymbol = this.symbolsById[symbolId];

		const exporter = new TextureAtlasExporter();
		exporter.filePath = folder;
		exporter.autoSize = true;
		exporter.resolution = 2;
		exporter.optimizeJson = false;
		exporter.imageFormat = "RGB8888";
		exporter.optimizeBitmap = true;

		exporter.exportTextureAtlas(rootSymbol.flSymbol);
	}

	dumpFramesForSymbol(fileSafeSymbolId, filepath) {
		const symbolId = fromValidFilename(fileSafeSymbolId);
		const result = [];
		this.sequencesBySymbolId[symbolId].forEach((seq) => {
			result.push(seq.map((x) => x.frameIndex));
		});
		logger.log(JSON.stringify(result));
	}

	dumpAllSequences(folder) {
		FLfile.createFolder(`file:///${folder}`);

		for (let symbolId in this.symbolsById) {
			const symbol = this.symbolsById[symbolId];
			const frameSets = this.framesBySymbolId.getCompact(symbolId);
			this.dumpSymbolSequences(symbol, frames, folder);
		}
	}

	debug() {
		let pendingConversions = Object.keys(this.animationFile.knownShapes);
		let total = pendingConversions.length;

		logger.log("total:", total);

		// pendingConversions.forEach((x) => logger.log(x));
	}

	_dumpShapeSpritesheetFromDocument(animationDoc, packer) {
		let newNames = {};
		let completed = Object.keys(newNames).length;
		let newlyCompleted = null;
		let failedConversions = [];

		const getAssetFromAnimationDoc = (assetName) => {
			const index = animationDoc.library.findItemIndex(newNames[assetName]);
			return animationDoc.library.items[index];
		}

		// enter the one symbol
		const flLayer = animationDoc.getTimeline().layers[0];
		const flSymbol = flLayer.frames[0].elements[0];
		flSymbol.selected = true
		animationDoc.enterEditMode("inPlace");

		const flTimeline = fl.getDocumentDOM().getTimeline();

		while(newlyCompleted !== 0) {
			newlyCompleted = 0;
			failedConversions = [];

			flTimeline.layers[0].frames.forEach((flFrame, id) => {
				if (id in newNames) {
					return;
				}

				const shapeName = `SynthShape_${id}_v2`;

				try {
					logger.log(`converting ${completed+1} / ${flTimeline.layers[0].frames.length}`);

					// select the shape
					
					flTimeline.currentFrame = id;
					const flElement = flFrame.elements[0];
					flElement.selected = true;
					
					// convert it to a symbol
					const width = flElement.width;
					const height = flElement.height;
					const transformX = flElement.transformX;
					const transformY = flElement.transformY;
					const flNewSymbol = animationDoc.convertToSymbol("graphic", shapeName, "center");

					if (!flNewSymbol) {
						return;
					}
					
					// add it to the packer
					newNames[id] = flNewSymbol.name;
					const meta = {
						id,
						transformX,
						transformY,
					};
					packer.addImage(() => getAssetFromAnimationDoc(id), meta, width, height, transformX, transformY);
					
					completed += 1;
					newlyCompleted += 1;
				} catch(err) {
					logger.log("delaying conversion for " + shapeName);
					logger.log(err);
				}
			});
		}

		return failedConversions;
	}

	_dumpPackerToSvg(shapeDoc, packer, folderPath) {
		shapeDoc.width = 8192;
		shapeDoc.height = 8192;
		const shapeTimeline = shapeDoc.getTimeline();
		const shapeLibrary = shapeDoc.library;
		const insertions = packer.toFrames(); // insertion[frameIndex] = { image, position }

		FLfile.createFolder(`file:///${folderPath}`);
		const spritemap = {};
		spritemap['sprites'] = [];
		spritemap['meta'] = {
			'app': 'Synthrunner - Pony Preservation Project',
			'version': '21.7.23.1',
			'format': 'svg',
			'size': {'w':8192, 'h':8192}
		}

		insertions.forEach((frame, frameIndex) => {
			if (frameIndex !== 0) {
				shapeTimeline.insertBlankKeyframe();
				shapeTimeline.currentFrame = frameIndex;
			}

			const imageName = `spritemap${frameIndex}.svg`
			const imagePath = `file:///${folderPath}/${imageName}`;

			frame.forEach(({image, position}) => {
				const shapeItem = image.data();

				if (position === null || !shapeItem) {
					logger.log("... skipping " + image.id);
				} else {
					position.dump("adding " + shapeItem.name)
					shapeDoc.addItem({ x:position.x(), y:position.y() }, shapeItem);	
					spritemap['sprites'].push({
						'id': image.meta.id,
						'filename': imageName,
						'svgObjectPrefix': shapeItem.name,
						'x': position.x(),
						'y': position.y(),
						'width': position.width(),
						'height': position.height(),
						'originX': image.meta.transformX,
						'originY': image.meta.transformY,
						'rescale': image.applyScale
					})
				}
			});

			shapeDoc.exportSVG(imagePath, true, true);
		})

		logger.log("done");
		FLfile.write(`file:///${folderPath}/spritemap.json`, JSON.stringify(spritemap, null, 4));

	}

	dumpShapeSpritesheet(folderPath) {
		const shapeNames = [];
		const animationDoc = fl.getDocumentDOM();
		const animationLibrary = animationDoc.library;
		const packer = new ImagePacker();

		animationDoc.currentTimeline = 0;
		this._dumpShapeSpritesheetFromDocument(animationDoc, packer);

		const shapeDoc = fl.createDocument("timeline");
		this._dumpPackerToSvg(shapeDoc, packer, folderPath);
		
		fl.closeDocument(shapeDoc, false);
	}

}

const getFrameFilename = (uri, frameIndex) => {
	const parts = uri.split(".");
	const extension = parts.pop();
	return `${parts.join(".")}${frameIndex.toString().padStart(4, 0)}.${extension}`;
}
