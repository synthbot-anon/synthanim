/******/ (function() { // webpackBootstrap
/******/ 	var __webpack_modules__ = ({

/***/ 766:
/***/ (function(__unused_webpack_module, exports, __webpack_require__) {

"use strict";
var __webpack_unused_export__;

__webpack_unused_export__ = true;
var synthrunner_js_1 = __webpack_require__(674);
var AnimationTree_js_1 = __webpack_require__(133);
var sourceFile = "%sourceFile";
var symbols = JSON.parse("%symbols");
synthrunner_js_1["default"](function (logger) {
    document = fl.openDocument("file:///" + sourceFile);
    var rootLayers = AnimationTree_js_1.getRootLayers();
    var exporter = new AnimationTree_js_1.SymbolExporter();
    rootLayers.map(function (rootLayer) {
        exporter.addSequences(rootLayer.getSequences());
    });
    symbols.forEach(function (_a) {
        var symName = _a[0], outputDir = _a[1];
        exporter.dumpTextureAtlas(symName, "file:///" + outputDir);
        exporter.dumpFramesForSymbol(symName);
    });
});


/***/ }),

/***/ 133:
/***/ (function(__unused_webpack_module, exports, __webpack_require__) {

"use strict";

exports.__esModule = true;
exports.SymbolExporter = exports.getRootLayers = void 0;
var synthrunner_js_1 = __webpack_require__(674);
var getRootLayers = function () {
    var timeline = fl.getDocumentDOM().getTimeline();
    var file = new AnimationFile();
    return timeline.layers.map(function (x, i) {
        var layerId = "L" + i;
        return new AnimationLayer(file, layerId, x);
    });
};
exports.getRootLayers = getRootLayers;
var toValidFilename = function (proposal) {
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
};
var fromValidFilename = function (filename) {
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
};
var AnimationFile = /** @class */ (function () {
    function AnimationFile() {
        this.knownSymbols = {};
        this.symbolIdFromGuid = {};
        this.knownLayers = {};
    }
    AnimationFile.prototype.getSymbolId = function (proposal, guid) {
        if (guid in this.symbolIdFromGuid) {
            return this.symbolIdFromGuid[guid];
        }
        this.symbolIdFromGuid[guid] = proposal;
        return proposal;
    };
    return AnimationFile;
}());
var AnimationSymbol = /** @class */ (function () {
    function AnimationSymbol(file, symbolId, flElement) {
        this.file = file;
        this.id = symbolId;
        this.flElement = flElement;
        this.flSymbol = flElement.libraryItem;
        this.timeline = flElement.libraryItem.timeline;
        this.names = {};
        this.frames = [];
    }
    AnimationSymbol.prototype.attachName = function (name) {
        this.names[name] = true;
    };
    AnimationSymbol.prototype.getNames = function () {
        return Object.keys(this.names).join(",");
    };
    AnimationSymbol.prototype.getLayerFromFLlayer = function (layerIndex, flLayer) {
        var layerId = this.id + "_L" + layerIndex;
        if (layerId in this.file.knownLayers) {
            return this.file.knownLayers[layerId];
        }
        var result = new AnimationLayer(this.file, layerId, flLayer);
        this.file.knownLayers[layerId] = result;
        return result;
    };
    AnimationSymbol.prototype.getLayers = function () {
        var _this = this;
        return this.timeline.layers.map(function (x, i) { return _this.getLayerFromFLlayer(i, x); });
    };
    AnimationSymbol.prototype.registerFrame = function (symbolFrame) {
        this.frames[symbolFrame.frameIndex] = symbolFrame;
    };
    return AnimationSymbol;
}());
var SymbolFrame = /** @class */ (function () {
    function SymbolFrame(symbol, frameIndex, flFrame) {
        this.symbol = symbol;
        this.frameIndex = frameIndex;
        this.flFrame = flFrame;
    }
    SymbolFrame.prototype.allSymbolFrames = function () {
        var result = [];
        var pending = [this];
        var _loop_1 = function () {
            var currentSymbolFrame = pending.pop();
            result.push(currentSymbolFrame);
            currentSymbolFrame.symbol.getLayers().forEach(function (childLayer) {
                var layerFrames = childLayer.getSymbolFrames(currentSymbolFrame.frameIndex);
                if (layerFrames === null) {
                    currentSymbolFrame.hasInvalidFrames = true;
                }
                else {
                    currentSymbolFrame.hasInvalidFrames = false;
                    pending.push.apply(pending, layerFrames);
                }
            });
        };
        while (pending.length !== 0) {
            _loop_1();
        }
        return result;
    };
    return SymbolFrame;
}());
var AnimationSequence = /** @class */ (function () {
    function AnimationSequence(symbol) {
        this.symbol = symbol;
        this.frames = [];
    }
    AnimationSequence.prototype.pushFrame = function (frame) {
        this.frames.push(frame);
    };
    return AnimationSequence;
}());
var SequenceGenerator = /** @class */ (function () {
    function SequenceGenerator() {
        this.completedSequences = [];
        this.touchedSequences = {};
        this.openSequences = {};
    }
    SequenceGenerator.prototype.placeSymbolFrame = function (symbolFrame) {
        var symbol = symbolFrame.symbol;
        var sequence;
        if (symbol.id in this.openSequences) {
            sequence = this.openSequences[symbol.id];
        }
        else {
            sequence = new AnimationSequence(symbol);
            this.openSequences[symbol.id] = sequence;
        }
        this.touchedSequences[symbol.id] = true;
        sequence.pushFrame(symbolFrame);
    };
    SequenceGenerator.prototype.nextFrame = function () {
        for (var prevOpenSymbol in this.openSequences) {
            if (!(prevOpenSymbol in this.touchedSequences)) {
                // broke the sequence, so whatever was there is complete
                var prevOpenSeq = this.openSequences[prevOpenSymbol];
                this.completedSequences.push(prevOpenSeq);
                delete this.openSequences[prevOpenSymbol];
            }
        }
        this.touchedSequences = {};
    };
    SequenceGenerator.prototype.getSequences = function () {
        this.nextFrame();
        this.nextFrame();
        return this.completedSequences;
    };
    return SequenceGenerator;
}());
var AnimationLayer = /** @class */ (function () {
    function AnimationLayer(file, layerId, flLayer) {
        this.file = file;
        this.id = layerId;
        this.flLayer = flLayer;
        this.name = flLayer.name;
    }
    AnimationLayer.prototype.getSymbolFromFLelement = function (frameIndex, elementIndex, flElement) {
        var symbolIdProposal = flElement.libraryItem.name;
        var symbolId = this.file.getSymbolId(symbolIdProposal, flElement.guid);
        if (symbolId in this.file.knownSymbols) {
            return this.file.knownSymbols[symbolId];
        }
        var result = new AnimationSymbol(this.file, symbolId, flElement);
        this.file.knownSymbols[symbolId] = result;
        return result;
    };
    AnimationLayer.prototype.getSequences = function () {
        var _this = this;
        var generator = new SequenceGenerator();
        for (var frameIndex = 0; frameIndex < this.flLayer.frames.length; frameIndex++) {
            this.getSymbolFrames(frameIndex).forEach(function (symbolFrame) {
                symbolFrame.symbol.attachName(_this.name);
                generator.placeSymbolFrame(symbolFrame);
            });
            generator.nextFrame();
        }
        return generator.getSequences();
    };
    AnimationLayer.prototype.getSymbolFrames = function (frameIndex) {
        var _this = this;
        var result = [];
        var flFrame = this.flLayer.frames[frameIndex];
        if (!flFrame) {
            // logger.log("invalid frame index", frameIndex, "for layer", this.name);
            return null;
        }
        flFrame.elements.forEach(function (flElement, elementIndex) {
            if (!elementHasFrames(flElement)) {
                return;
            }
            var symbol = _this.getSymbolFromFLelement(frameIndex, elementIndex, flElement);
            symbol.attachName(_this.name);
            var symbolDisplayIndex = getSymbolDisplayIndex(flFrame, frameIndex, flElement);
            var symbolFrame = new SymbolFrame(symbol, symbolDisplayIndex, flFrame);
            symbol.registerFrame(symbolFrame);
            result.push(symbolFrame);
        });
        return result;
    };
    return AnimationLayer;
}());
var elementHasFrames = function (flElement) {
    if (!('symbolType' in flElement)) {
        return false;
    }
    if (flElement.symbolType === "movie clip") {
        return false;
    }
    return true;
};
var getSymbolDisplayIndex = function (flFrame, frameIndex, flElement) {
    var symbolFrameIter = frameIndex - flFrame.startFrame;
    var symbolLastFrame = ((flElement.lastFrame === -1)
        ? flElement.libraryItem.timeline.frameCount
        : flElement.lastFrame);
    var symbolDisplayIndex;
    if (flElement.loop === "single frame") {
        symbolDisplayIndex = flElement.firstFrame;
    }
    else if (flElement.loop === "play once") {
        symbolDisplayIndex = Math.floor(flElement.firstFrame + symbolFrameIter, symbolLastFrame - 1);
    }
    else if (flElement.loop === "loop") {
        symbolDisplayIndex = flElement.firstFrame + (symbolFrameIter % (symbolLastFrame - flElement.firstFrame));
    }
    else {
        synthrunner_js_1.logger.log("unknown loop type:", flElement.loop, "in");
        synthrunner_js_1.logger.log("elementType:", flElement.elementType);
        synthrunner_js_1.logger.log("instanceType:", flElement.instanceType);
        synthrunner_js_1.logger.log("symbolType:", flElement.symbolType);
        synthrunner_js_1.logger.log("effectSymbol:", flElement.effectSymbol);
        synthrunner_js_1.logger.logProperties(flElement);
    }
    return symbolDisplayIndex;
};
var ArrayMaps = /** @class */ (function () {
    function ArrayMaps() {
        this.knownMaps = {};
    }
    ArrayMaps.prototype.set = function (arrayId, arrayIndex, value) {
        var knownMap = this.knownMaps[arrayId];
        if (!knownMap) {
            knownMap = [];
            this.knownMaps[arrayId] = knownMap;
        }
        knownMap[arrayIndex] = value;
    };
    ArrayMaps.prototype.push = function (arrayId, value) {
        var offset = (this.get(arrayId) || []).length;
        this.set(arrayId, offset, value);
    };
    ArrayMaps.prototype.get = function (arrayId, arrayIndex) {
        var arrayResult = this.knownMaps[arrayId];
        if (arrayIndex !== undefined) {
            return arrayResult[arrayIndex];
        }
        return arrayResult;
    };
    ArrayMaps.prototype.getCompact = function (arrayId) {
        var result = [];
        var keys = Object.keys(this.knownMaps[arrayId]);
        if (keys.length === 0) {
            return result;
        }
        var nextBatch = null;
        for (var _i = 0, keys_1 = keys; _i < keys_1.length; _i++) {
            var nextKey = keys_1[_i];
            if (nextBatch && (nextKey - 1 === nextBatch[nextBatch.length - 1])) {
                nextBatch.push(nextKey);
            }
            else {
                if (nextBatch) {
                    result.push(nextBatch);
                }
                nextBatch = [nextKey];
            }
        }
        return result;
    };
    return ArrayMaps;
}());
var SymbolExporter = /** @class */ (function () {
    function SymbolExporter() {
        this.sequences = [];
        this.framesBySymbolId = new ArrayMaps();
        this.symbolsById = {};
        this.sequencesBySymbolId = {};
    }
    SymbolExporter.prototype.addSequences = function (sequences) {
        var _this = this;
        var generator = new SequenceGenerator();
        sequences.forEach(function (seq) {
            seq.frames.map(function (sequenceFrame) {
                for (var _i = 0, _a = sequenceFrame.allSymbolFrames(); _i < _a.length; _i++) {
                    var componentFrame = _a[_i];
                    generator.placeSymbolFrame(componentFrame);
                    _this.symbolsById[componentFrame.symbol.id] = componentFrame.symbol;
                    _this.framesBySymbolId.set(componentFrame.symbol.id, componentFrame.frameIndex, true);
                }
            });
        });
        generator.getSequences().forEach(function (seq) {
            var knownSequences = _this.sequencesBySymbolId[seq.symbol.id] || [];
            knownSequences.push(seq.frames);
            _this.sequencesBySymbolId[seq.symbol.id] = knownSequences;
        });
    };
    SymbolExporter.prototype.getSymbolsByName = function (name) {
        var result = [];
        for (var id in this.symbolsById) {
            var symbol = this.symbolsById[id];
            if (name in symbol.names) {
                result.push(symbol);
            }
        }
        return result;
    };
    SymbolExporter.prototype.getAllSymbolNames = function () {
        var result = [];
        for (var id in this.symbolsById) {
            var symbol = this.symbolsById[id];
            result.push.apply(result, Object.keys(symbol.names));
        }
        return result;
    };
    SymbolExporter.prototype.getMedianFrame = function (symbol) {
        var frames = Object.keys(this.framesBySymbolId.get(symbol.id));
        frames.sort();
        var offset = Math.floor(frames.length / 2);
        return parseInt(frames[offset]);
    };
    SymbolExporter.prototype.dumpSymbolSample = function (symbol, folder) {
        var frameIndex = this.getMedianFrame(symbol);
        var exporter = new SpriteSheetExporter();
        var spriteFilename = toValidFilename(symbol.id);
        var spritePath = "file:///" + folder + "/" + spriteFilename + "_f.png";
        try {
            symbol.flSymbol.exportToPNGSequence(spritePath, frameIndex + 1, frameIndex + 1);
        }
        catch (err) {
            synthrunner_js_1.logger.log("failed to convert", symbol.id);
        }
        var framePath = getFrameFilename(spritePath, frameIndex + 2);
        FLfile.remove(framePath);
    };
    SymbolExporter.prototype.dumpAllSymbolSamples = function (folder) {
        FLfile.createFolder("file:///" + folder);
        for (var symbolId in this.symbolsById) {
            var symbol = this.symbolsById[symbolId];
            this.dumpSymbolSample(symbol, folder);
        }
    };
    SymbolExporter.prototype.dumpTextureAtlas = function (fileSafeSymbolId, folder) {
        var symbolId = fromValidFilename(fileSafeSymbolId);
        synthrunner_js_1.logger.log("symbol:", symbolId);
        var rootSymbol = this.symbolsById[symbolId];
        var exporter = new TextureAtlasExporter();
        exporter.filePath = folder;
        exporter.autoSize = true;
        exporter.resolution = 2;
        exporter.optimizeJson = false;
        exporter.imageFormat = "RGB8888";
        exporter.optimizeBitmap = true;
        exporter.exportTextureAtlas(rootSymbol.flSymbol);
    };
    SymbolExporter.prototype.dumpFramesForSymbol = function (fileSafeSymbolId, filepath) {
        var symbolId = fromValidFilename(fileSafeSymbolId);
        var result = [];
        this.sequencesBySymbolId[symbolId].forEach(function (seq) {
            result.push(seq.map(function (x) { return x.frameIndex; }));
        });
        synthrunner_js_1.logger.log(JSON.stringify(result));
    };
    SymbolExporter.prototype.dumpAllSequences = function (folder) {
        FLfile.createFolder("file:///" + folder);
        for (var symbolId in this.symbolsById) {
            var symbol = this.symbolsById[symbolId];
            var frameSets = this.framesBySymbolId.getCompact(symbolId);
            this.dumpSymbolSequences(symbol, frames, folder);
        }
    };
    return SymbolExporter;
}());
exports.SymbolExporter = SymbolExporter;
var getFrameFilename = function (uri, frameIndex) {
    var parts = uri.split(".");
    var extension = parts.pop();
    return "" + parts.join(".") + frameIndex.toString().padStart(4, 0) + "." + extension;
};


/***/ }),

/***/ 658:
/***/ (function() {

// From https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Object/keys
if (!Object.keys) {
    Object.keys = (function () {
        'use strict';
        var hasOwnProperty = Object.prototype.hasOwnProperty, hasDontEnumBug = !({ toString: null }).propertyIsEnumerable('toString'), dontEnums = [
            'toString',
            'toLocaleString',
            'valueOf',
            'hasOwnProperty',
            'isPrototypeOf',
            'propertyIsEnumerable',
            'constructor'
        ], dontEnumsLength = dontEnums.length;
        return function (obj) {
            if (typeof obj !== 'function' && (typeof obj !== 'object' || obj === null)) {
                throw new TypeError('Object.keys called on non-object');
            }
            var result = [], prop, i;
            for (prop in obj) {
                if (hasOwnProperty.call(obj, prop)) {
                    result.push(prop);
                }
            }
            if (hasDontEnumBug) {
                for (i = 0; i < dontEnumsLength; i++) {
                    if (hasOwnProperty.call(obj, dontEnums[i])) {
                        result.push(dontEnums[i]);
                    }
                }
            }
            return result;
        };
    }());
}
/**
 * String.fromCharCode()
 * version 0.0.0
 * Feature          Chrome  Firefox Internet Explorer   Opera Safari  Edge
 * Basic support  (Yes)   (Yes)   (Yes)             (Yes) (Yes)   (Yes)
 * -------------------------------------------------------------------------------
 */
/**
 * String.fromCodePoint()
 * version 0.0.0
 * Feature          Chrome  Firefox Internet Explorer   Opera Safari  Edge
 * Basic support  41    29      (No)              28      10      ?
 * -------------------------------------------------------------------------------
 */
if (!String.fromCodePoint) {
    (function () {
        var defineProperty = (function () {
            try {
                var object = {};
                var $defineProperty = Object.defineProperty;
                var result = $defineProperty(object, object, object) && $defineProperty;
            }
            catch (error) { }
            return result;
        })();
        var stringFromCharCode = String.fromCharCode;
        var floor = Math.floor;
        var fromCodePoint = function () {
            var MAX_SIZE = 0x4000;
            var codeUnits = [];
            var highSurrogate;
            var lowSurrogate;
            var index = -1;
            var length = arguments.length;
            if (!length) {
                return '';
            }
            var result = '';
            while (++index < length) {
                var codePoint = Number(arguments[index]);
                if (!isFinite(codePoint) ||
                    codePoint < 0 ||
                    codePoint > 0x10ffff ||
                    floor(codePoint) != codePoint) {
                    throw RangeError('Invalid code point: ' + codePoint);
                }
                if (codePoint <= 0xffff) {
                    // BMP code point
                    codeUnits.push(codePoint);
                }
                else {
                    codePoint -= 0x10000;
                    highSurrogate = (codePoint >> 10) + 0xd800;
                    lowSurrogate = (codePoint % 0x400) + 0xdc00;
                    codeUnits.push(highSurrogate, lowSurrogate);
                }
                if (index + 1 == length || codeUnits.length > MAX_SIZE) {
                    result += stringFromCharCode.apply(null, codeUnits);
                    codeUnits.length = 0;
                }
            }
            return result;
        };
        if (defineProperty) {
            defineProperty(String, 'fromCodePoint', {
                value: fromCodePoint,
                configurable: true,
                writable: true
            });
        }
        else {
            String.fromCodePoint = fromCodePoint;
        }
    })();
}
/**
 * String.anchor()
 * version 0.0.0
 * Feature          Chrome  Firefox Internet Explorer   Opera Safari  Edge
 * Basic support  (Yes)   1.0     (Yes)             (Yes) (Yes)   (Yes)
 * -------------------------------------------------------------------------------
 */
/**
 * String.charAt()
 * version 0.0.0
 * Feature          Chrome  Firefox Internet Explorer   Opera Safari  Edge
 * Basic support  (Yes)   (Yes)   (Yes)             (Yes) (Yes)   (Yes)
 * -------------------------------------------------------------------------------
 */
/**
 * String.charCodeAt()
 * version 0.0.0
 * Feature          Chrome  Firefox Internet Explorer   Opera Safari  Edge
 * Basic support  (Yes)   1.0     (Yes)             (Yes) (Yes)   (Yes)
 * -------------------------------------------------------------------------------
 */
/**
 * String.codePointAt()
 * version 0.0.0
 * Feature          Chrome  Firefox Internet Explorer   Opera Safari  Edge
 * Basic support  41    29      11                  28      10      ?
 * -------------------------------------------------------------------------------
 */
if (!String.prototype.codePointAt) {
    (function () {
        'use strict';
        var codePointAt = function (position) {
            if (this == null) {
                throw TypeError();
            }
            var string = String(this);
            var size = string.length;
            var index = position ? Number(position) : 0;
            if (index != index) {
                index = 0;
            }
            if (index < 0 || index >= size) {
                return undefined;
            }
            var first = string.charCodeAt(index);
            var second;
            if (first >= 0xd800 && first <= 0xdbff && size > index + 1) {
                second = string.charCodeAt(index + 1);
                if (second >= 0xdc00 && second <= 0xdfff) {
                    return (first - 0xd800) * 0x400 + second - 0xdc00 + 0x10000;
                }
            }
            return first;
        };
        if (Object.defineProperty) {
            Object.defineProperty(String.prototype, 'codePointAt', {
                value: codePointAt,
                configurable: true,
                writable: true
            });
        }
        else {
            String.prototype.codePointAt = codePointAt;
        }
    })();
}
/**
 * String.concat()
 * version 0.0.0
 * Feature          Chrome  Firefox Internet Explorer   Opera Safari  Edge
 * Basic support  (Yes)   (Yes)   (Yes)             (Yes) (Yes)   (Yes)
 * -------------------------------------------------------------------------------
 */
/**
 * String.endsWith()
 * version 0.0.0
 * Feature          Chrome  Firefox Internet Explorer   Opera Safari  Edge
 * Basic support  41    17      (No)              (No)  9       (Yes)
 * -------------------------------------------------------------------------------
 */
if (!String.prototype.endsWith) {
    String.prototype.endsWith = function (searchString, position) {
        var subjectString = this.toString();
        if (typeof position !== 'number' ||
            !isFinite(position) ||
            Math.floor(position) !== position ||
            position > subjectString.length) {
            position = subjectString.length;
        }
        position -= searchString.length;
        var lastIndex = subjectString.lastIndexOf(searchString, position);
        return lastIndex !== -1 && lastIndex === position;
    };
}
/**
 * String.includes()
 * version 0.0.0
 * Feature          Chrome  Firefox Internet Explorer   Opera Safari  Edge
 * Basic support  41    40      (No)              (No)  9       (Yes)
 * -------------------------------------------------------------------------------
 */
if (!String.prototype.includes) {
    String.prototype.includes = function (search, start) {
        'use strict';
        if (typeof start !== 'number') {
            start = 0;
        }
        if (start + search.length > this.length) {
            return false;
        }
        else {
            return this.indexOf(search, start) !== -1;
        }
    };
}
/**
 * String.indexOf()
 * version 0.0.0
 * Feature          Chrome  Firefox Internet Explorer   Opera Safari  Edge
 * Basic support  (Yes)   (Yes)   (Yes)             (Yes) (Yes)   (Yes)
 * -------------------------------------------------------------------------------
 */
/**
 * String.lastIndexOf()
 * version 0.0.0
 * Feature          Chrome  Firefox Internet Explorer   Opera Safari  Edge
 * Basic support  (Yes)   (Yes)   (Yes)             (Yes) (Yes)   (Yes)
 * -------------------------------------------------------------------------------
 */
/**
 * String.link()
 * version 0.0.0
 * Feature          Chrome  Firefox Internet Explorer   Opera Safari  Edge
 * Basic support  (Yes)   1.0    (Yes)              (Yes) (Yes)   (Yes)
 * -------------------------------------------------------------------------------
 */
/**
 * String.localeCompare()
 * version 0.0.0
 * Feature          Chrome  Firefox Internet Explorer   Opera Safari  Edge
 * Basic support  (Yes)   1.0    (Yes)              (Yes) (Yes)   (Yes)
 * -------------------------------------------------------------------------------
 */
/**
 * String.match()
 * version 0.0.0
 * Feature          Chrome  Firefox Internet Explorer   Opera Safari  Edge
 * Basic support  (Yes)   (Yes)   (Yes)             (Yes) (Yes)   (Yes)
 * -------------------------------------------------------------------------------
 */
/**
 * String.normalize()
 * version 0.0.1
 * Feature          Chrome  Firefox Internet Explorer   Opera Safari  Edge
 * Basic support  34    31      (No)              (Yes) 10      (Yes)
 * -------------------------------------------------------------------------------
 */
if (!String.prototype.normalize) {
    // need polyfill
}
/**
 * String.padEnd()
 * version 1.0.1
 * Feature          Chrome  Firefox Internet Explorer   Opera Safari  Edge
 * Basic support  57    48      (No)              44    10      15
 * -------------------------------------------------------------------------------
 */
if (!String.prototype.padEnd) {
    String.prototype.padEnd = function padEnd(targetLength, padString) {
        targetLength = targetLength >> 0; //floor if number or convert non-number to 0;
        padString = String(typeof padString !== 'undefined' ? padString : ' ');
        if (this.length > targetLength) {
            return String(this);
        }
        else {
            targetLength = targetLength - this.length;
            if (targetLength > padString.length) {
                padString += padString.repeat(targetLength / padString.length); //append to original to ensure we are longer than needed
            }
            return String(this) + padString.slice(0, targetLength);
        }
    };
}
/**
 * String.padStart()
 * version 1.0.1
 * Feature          Chrome  Firefox Internet Explorer   Opera Safari  Edge
 * Basic support  57    51      (No)              44    10      15
 * -------------------------------------------------------------------------------
 */
if (!String.prototype.padStart) {
    String.prototype.padStart = function padStart(targetLength, padString) {
        targetLength = targetLength >> 0; //floor if number or convert non-number to 0;
        padString = String(typeof padString !== 'undefined' ? padString : ' ');
        if (this.length > targetLength) {
            return String(this);
        }
        else {
            targetLength = targetLength - this.length;
            if (targetLength > padString.length) {
                padString += padString.repeat(targetLength / padString.length); //append to original to ensure we are longer than needed
            }
            return padString.slice(0, targetLength) + String(this);
        }
    };
}
/**
 * String.repeat()
 * version 0.0.0
 * Feature          Chrome  Firefox Internet Explorer   Opera Safari  Edge
 * Basic support  41    24      (No)              (Yes)   9       (Yes)
 * -------------------------------------------------------------------------------
 */
if (!String.prototype.repeat) {
    String.prototype.repeat = function (count) {
        'use strict';
        if (this == null) {
            throw new TypeError("can't convert " + this + ' to object');
        }
        var str = '' + this;
        count = +count;
        if (count != count) {
            count = 0;
        }
        if (count < 0) {
            throw new RangeError('repeat count must be non-negative');
        }
        if (count == Infinity) {
            throw new RangeError('repeat count must be less than infinity');
        }
        count = Math.floor(count);
        if (str.length == 0 || count == 0) {
            return '';
        }
        if (str.length * count >= 1 << 28) {
            throw new RangeError('repeat count must not overflow maximum string size');
        }
        var rpt = '';
        for (;;) {
            if ((count & 1) == 1) {
                rpt += str;
            }
            count >>>= 1;
            if (count == 0) {
                break;
            }
            str += str;
        }
        return rpt;
    };
}
/**
 * String.search()
 * version 0.0.0
 * Feature          Chrome  Firefox Internet Explorer   Opera Safari  Edge
 * Basic support  (Yes)   (Yes)   (Yes)             (Yes) (Yes)   (Yes)
 * -------------------------------------------------------------------------------
 */
/**
 * String.slice()
 * version 0.0.0
 * Feature          Chrome  Firefox Internet Explorer   Opera Safari  Edge
 * Basic support  (Yes)   (Yes)   (Yes)             (Yes) (Yes)   (Yes)
 * -------------------------------------------------------------------------------
 */
/**
 * String.split()
 * version 0.0.0
 * Feature          Chrome  Firefox Internet Explorer   Opera Safari  Edge
 * Basic support  (Yes)   (Yes)   (Yes)             (Yes) (Yes)   (Yes)
 * -------------------------------------------------------------------------------
 */
/**
 * String.startsWith()
 * version 0.0.0
 * Feature          Chrome  Firefox Internet Explorer   Opera Safari  Edge
 * Basic support  41    17      (No)              28    9       (Yes)
 * -------------------------------------------------------------------------------
 */
if (!String.prototype.startsWith) {
    String.prototype.startsWith = function (searchString, position) {
        position = position || 0;
        return this.substr(position, searchString.length) === searchString;
    };
}
/**
 * String.substr()
 * version 0.0.0
 * Feature          Chrome  Firefox Internet Explorer   Opera Safari  Edge
 * Basic support  (Yes)   (Yes)   (Yes)             (Yes) (Yes)   (Yes)
 * -------------------------------------------------------------------------------
 */
/**
 * String.substring()
 * version 0.0.0
 * Feature          Chrome  Firefox Internet Explorer   Opera Safari  Edge
 * Basic support  (Yes)   (Yes)   (Yes)             (Yes) (Yes)   (Yes)
 * -------------------------------------------------------------------------------
 */
/**
 * String.toLocaleLowerCase()
 * version 0.0.0
 * Feature          Chrome  Firefox Internet Explorer   Opera Safari  Edge
 * Basic support  (Yes)   (Yes)   (Yes)             (Yes) (Yes)   (Yes)
 * -------------------------------------------------------------------------------
 */
/**
 * String.toLocaleUpperCase()
 * version 0.0.0
 * Feature          Chrome  Firefox Internet Explorer   Opera Safari  Edge
 * Basic support  (Yes)   (Yes)   (Yes)             (Yes) (Yes)   (Yes)
 * -------------------------------------------------------------------------------
 */
/**
 * String.toLowerCase()
 * version 0.0.0
 * Feature          Chrome  Firefox Internet Explorer   Opera Safari  Edge
 * Basic support  (Yes)   (Yes)   (Yes)             (Yes) (Yes)   (Yes)
 * -------------------------------------------------------------------------------
 */
/**
 * String.toString()
 * version 0.0.0
 * Feature          Chrome  Firefox Internet Explorer   Opera Safari  Edge
 * Basic support  (Yes)   (Yes)   (Yes)             (Yes) (Yes)   (Yes)
 * -------------------------------------------------------------------------------
 */
/**
 * String.toUpperCase()
 * version 0.0.0
 * Feature          Chrome  Firefox Internet Explorer   Opera Safari  Edge
 * Basic support  (Yes)   (Yes)   (Yes)             (Yes) (Yes)   (Yes)
 * -------------------------------------------------------------------------------
 */
/**
 * String.trim()
 * version 0.0.0
 * Feature          Chrome  Firefox Internet Explorer   Opera Safari  Edge
 * Basic support  (Yes)   3.5     9                 10.5  5       ?
 * -------------------------------------------------------------------------------
 */
if (!String.prototype.trim) {
    String.prototype.trim = function () {
        return this.replace(/^[\s\uFEFF\xA0]+|[\s\uFEFF\xA0]+$/g, '');
    };
}
/**
 * String.trimLeft()
 * version 0.0.0
 * Feature          Chrome  Firefox Internet Explorer   Opera Safari  Edge
 * Basic support  (Yes)   3.5     (No)              ?     ?       ?
 * -------------------------------------------------------------------------------
 */
/**
 * String.trimRight()
 * version 0.0.0
 * Feature          Chrome  Firefox Internet Explorer   Opera Safari  Edge
 * Basic support  (Yes)   3.5     (No)              ?     ?       ?
 * -------------------------------------------------------------------------------
 */
/**
 * String.valueOf()
 * version 0.0.0
 * Feature          Chrome  Firefox Internet Explorer   Opera Safari  Edge
 * Basic support  (Yes)   (Yes)   (Yes)             (Yes) (Yes)   (Yes)
 * -------------------------------------------------------------------------------
 */
/**
 * String.raw
 * version 0.0.0
 * Feature          Chrome  Firefox Internet Explorer   Opera Safari  Edge
 * Basic support  41    34      (No)                (No)  10      ?
 * -------------------------------------------------------------------------------
 */
/**
* String.prototype.replaceAll() polyfill
* https://gomakethings.com/how-to-replace-a-section-of-a-string-with-another-one-with-vanilla-js/
* @author Chris Ferdinandi
* @license MIT
*/
if (!String.prototype.replaceAll) {
    String.prototype.replaceAll = function (str, newStr) {
        // If a regex pattern
        if (Object.prototype.toString.call(str).toLowerCase() === '[object regexp]') {
            return this.replace(str, newStr);
        }
        // If a string
        return this.replace(new RegExp(str, 'g'), newStr);
    };
}
if (!String.prototype.toLowerCase) {
    String.prototype.toLowerCase = function () {
        // TODO: Support Unicode characters.
        if (this === null || this === undefined) {
            throw TypeError('"this" is null or undefined');
        }
        var str = '' + this;
        var lower = 'abcdefghijklmnopqrstuvwxyz';
        var upper = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ';
        var outStr = '';
        for (var i = 0; i < str.length; i++) {
            var x = upper.indexOf(str[i]);
            if (x == -1) {
                outStr += str[i];
            }
            else {
                outStr += lower[x];
            }
        }
        return outStr;
    };
}
/*! http://mths.be/regexp-prototype-match v0.1.0 by @mathias */
if (!RegExp.prototype.match) {
    (function () {
        var defineProperty = (function () {
            // IE 8 only supports `Object.defineProperty` on DOM elements.
            try {
                var object = {};
                var $defineProperty = Object.defineProperty;
                var result = $defineProperty(object, object, object) && $defineProperty;
            }
            catch (exception) { }
            return result;
        }());
        var object = {};
        var toString = object.toString;
        var RegExpExec = function (R, S) {
            // This is an implementation of http://mths.be/es6#sec-regexpexec, with
            // the redundant steps for this particular use case omitted.
            if (typeof R.exec == 'function') {
                var result = R.exec(S);
                if (typeof result != 'object') {
                    throw TypeError();
                }
                return result;
            }
            if (toString.call(R) != '[object RegExp]') {
                throw TypeError();
            }
            return RegExp.prototype.exec.call(R, S);
        };
        var match = function (string) {
            var rx = this;
            if (rx === null || typeof rx != 'object') {
                throw TypeError();
            }
            var S = String(string);
            var global = Boolean(rx.global);
            if (global !== true) {
                return RegExpExec(rx, S);
            }
            rx.lastIndex = 0;
            var A = [];
            var previousLastIndex = 0;
            var n = 0;
            while (true) {
                var result = RegExpExec(rx, S);
                if (result === null) {
                    return n == 0 ? result : A;
                }
                var matchStr = result[0];
                A[n] = matchStr;
                ++n;
            }
        };
        if (defineProperty) {
            defineProperty(RegExp.prototype, 'match', {
                'value': match,
                'configurable': true,
                'writable': true
            });
        }
        else {
            RegExp.prototype.match = match;
        }
    }());
}
// Create a JSON object only if one does not already exist. We create the
// methods in a closure to avoid creating global variables.
if (typeof JSON !== "object") {
    JSON = {};
}
(function () {
    "use strict";
    var rx_one = /^[\],:{}\s]*$/;
    var rx_two = /\\(?:["\\\/bfnrt]|u[0-9a-fA-F]{4})/g;
    var rx_three = /"[^"\\\n\r]*"|true|false|null|-?\d+(?:\.\d*)?(?:[eE][+\-]?\d+)?/g;
    var rx_four = /(?:^|:|,)(?:\s*\[)+/g;
    var rx_escapable = /[\\"\u0000-\u001f\u007f-\u009f\u00ad\u0600-\u0604\u070f\u17b4\u17b5\u200c-\u200f\u2028-\u202f\u2060-\u206f\ufeff\ufff0-\uffff]/g;
    var rx_dangerous = /[\u0000\u00ad\u0600-\u0604\u070f\u17b4\u17b5\u200c-\u200f\u2028-\u202f\u2060-\u206f\ufeff\ufff0-\uffff]/g;
    function f(n) {
        // Format integers to have at least two digits.
        return (n < 10)
            ? "0" + n
            : n;
    }
    function this_value() {
        return this.valueOf();
    }
    if (typeof Date.prototype.toJSON !== "function") {
        Date.prototype.toJSON = function () {
            return isFinite(this.valueOf())
                ? (this.getUTCFullYear()
                    + "-"
                    + f(this.getUTCMonth() + 1)
                    + "-"
                    + f(this.getUTCDate())
                    + "T"
                    + f(this.getUTCHours())
                    + ":"
                    + f(this.getUTCMinutes())
                    + ":"
                    + f(this.getUTCSeconds())
                    + "Z")
                : null;
        };
        Boolean.prototype.toJSON = this_value;
        Number.prototype.toJSON = this_value;
        String.prototype.toJSON = this_value;
    }
    var gap;
    var indent;
    var meta;
    var rep;
    function quote(string) {
        // If the string contains no control characters, no quote characters, and no
        // backslash characters, then we can safely slap some quotes around it.
        // Otherwise we must also replace the offending characters with safe escape
        // sequences.
        rx_escapable.lastIndex = 0;
        return rx_escapable.test(string)
            ? "\"" + string.replace(rx_escapable, function (a) {
                var c = meta[a];
                return typeof c === "string"
                    ? c
                    : "\\u" + ("0000" + a.charCodeAt(0).toString(16)).slice(-4);
            }) + "\""
            : "\"" + string + "\"";
    }
    function str(key, holder) {
        // Produce a string from holder[key].
        var i; // The loop counter.
        var k; // The member key.
        var v; // The member value.
        var length;
        var mind = gap;
        var partial;
        var value = holder[key];
        // If the value has a toJSON method, call it to obtain a replacement value.
        if (value
            && typeof value === "object"
            && typeof value.toJSON === "function") {
            value = value.toJSON(key);
        }
        // If we were called with a replacer function, then call the replacer to
        // obtain a replacement value.
        if (typeof rep === "function") {
            value = rep.call(holder, key, value);
        }
        // What happens next depends on the value's type.
        switch (typeof value) {
            case "string":
                return quote(value);
            case "number":
                // JSON numbers must be finite. Encode non-finite numbers as null.
                return (isFinite(value))
                    ? String(value)
                    : "null";
            case "boolean":
            case "null":
                // If the value is a boolean or null, convert it to a string. Note:
                // typeof null does not produce "null". The case is included here in
                // the remote chance that this gets fixed someday.
                return String(value);
            // If the type is "object", we might be dealing with an object or an array or
            // null.
            case "object":
                // Due to a specification blunder in ECMAScript, typeof null is "object",
                // so watch out for that case.
                if (!value) {
                    return "null";
                }
                // Make an array to hold the partial results of stringifying this object value.
                gap += indent;
                partial = [];
                // Is the value an array?
                if (Object.prototype.toString.apply(value) === "[object Array]") {
                    // The value is an array. Stringify every element. Use null as a placeholder
                    // for non-JSON values.
                    length = value.length;
                    for (i = 0; i < length; i += 1) {
                        partial[i] = str(i, value) || "null";
                    }
                    // Join all of the elements together, separated with commas, and wrap them in
                    // brackets.
                    v = partial.length === 0
                        ? "[]"
                        : gap
                            ? ("[\n"
                                + gap
                                + partial.join(",\n" + gap)
                                + "\n"
                                + mind
                                + "]")
                            : "[" + partial.join(",") + "]";
                    gap = mind;
                    return v;
                }
                // If the replacer is an array, use it to select the members to be stringified.
                if (rep && typeof rep === "object") {
                    length = rep.length;
                    for (i = 0; i < length; i += 1) {
                        if (typeof rep[i] === "string") {
                            k = rep[i];
                            v = str(k, value);
                            if (v) {
                                partial.push(quote(k) + ((gap)
                                    ? ": "
                                    : ":") + v);
                            }
                        }
                    }
                }
                else {
                    // Otherwise, iterate through all of the keys in the object.
                    for (k in value) {
                        if (Object.prototype.hasOwnProperty.call(value, k)) {
                            v = str(k, value);
                            if (v) {
                                partial.push(quote(k) + ((gap)
                                    ? ": "
                                    : ":") + v);
                            }
                        }
                    }
                }
                // Join all of the member texts together, separated with commas,
                // and wrap them in braces.
                v = partial.length === 0
                    ? "{}"
                    : gap
                        ? "{\n" + gap + partial.join(",\n" + gap) + "\n" + mind + "}"
                        : "{" + partial.join(",") + "}";
                gap = mind;
                return v;
        }
    }
    // If the JSON object does not yet have a stringify method, give it one.
    if (typeof JSON.stringify !== "function") {
        meta = {
            "\b": "\\b",
            "\t": "\\t",
            "\n": "\\n",
            "\f": "\\f",
            "\r": "\\r",
            "\"": "\\\"",
            "\\": "\\\\"
        };
        JSON.stringify = function (value, replacer, space) {
            // The stringify method takes a value and an optional replacer, and an optional
            // space parameter, and returns a JSON text. The replacer can be a function
            // that can replace values, or an array of strings that will select the keys.
            // A default replacer method can be provided. Use of the space parameter can
            // produce text that is more easily readable.
            var i;
            gap = "";
            indent = "";
            // If the space parameter is a number, make an indent string containing that
            // many spaces.
            if (typeof space === "number") {
                for (i = 0; i < space; i += 1) {
                    indent += " ";
                }
                // If the space parameter is a string, it will be used as the indent string.
            }
            else if (typeof space === "string") {
                indent = space;
            }
            // If there is a replacer, it must be a function or an array.
            // Otherwise, throw an error.
            rep = replacer;
            if (replacer && typeof replacer !== "function" && (typeof replacer !== "object"
                || typeof replacer.length !== "number")) {
                throw new Error("JSON.stringify");
            }
            // Make a fake root object containing our value under the key of "".
            // Return the result of stringifying the value.
            return str("", { "": value });
        };
    }
    // If the JSON object does not yet have a parse method, give it one.
    if (typeof JSON.parse !== "function") {
        JSON.parse = function (text, reviver) {
            // The parse method takes a text and an optional reviver function, and returns
            // a JavaScript value if the text is a valid JSON text.
            var j;
            function walk(holder, key) {
                // The walk method is used to recursively walk the resulting structure so
                // that modifications can be made.
                var k;
                var v;
                var value = holder[key];
                if (value && typeof value === "object") {
                    for (k in value) {
                        if (Object.prototype.hasOwnProperty.call(value, k)) {
                            v = walk(value, k);
                            if (v !== undefined) {
                                value[k] = v;
                            }
                            else {
                                delete value[k];
                            }
                        }
                    }
                }
                return reviver.call(holder, key, value);
            }
            // Parsing happens in four stages. In the first stage, we replace certain
            // Unicode characters with escape sequences. JavaScript handles many characters
            // incorrectly, either silently deleting them, or treating them as line endings.
            text = String(text);
            rx_dangerous.lastIndex = 0;
            if (rx_dangerous.test(text)) {
                text = text.replace(rx_dangerous, function (a) {
                    return ("\\u"
                        + ("0000" + a.charCodeAt(0).toString(16)).slice(-4));
                });
            }
            // In the second stage, we run the text against regular expressions that look
            // for non-JSON patterns. We are especially concerned with "()" and "new"
            // because they can cause invocation, and "=" because it can cause mutation.
            // But just to be safe, we want to reject all unexpected forms.
            // We split the second stage into 4 regexp operations in order to work around
            // crippling inefficiencies in IE's and Safari's regexp engines. First we
            // replace the JSON backslash pairs with "@" (a non-JSON character). Second, we
            // replace all simple value tokens with "]" characters. Third, we delete all
            // open brackets that follow a colon or comma or that begin the text. Finally,
            // we look to see that the remaining characters are only whitespace or "]" or
            // "," or ":" or "{" or "}". If that is so, then the text is safe for eval.
            if (rx_one.test(text
                .replace(rx_two, "@")
                .replace(rx_three, "]")
                .replace(rx_four, ""))) {
                // In the third stage we use the eval function to compile the text into a
                // JavaScript structure. The "{" operator is subject to a syntactic ambiguity
                // in JavaScript: it can begin a block or an object literal. We wrap the text
                // in parens to eliminate the ambiguity.
                j = eval("(" + text + ")");
                // In the optional fourth stage, we recursively walk the new structure, passing
                // each name/value pair to a reviver function for possible transformation.
                return (typeof reviver === "function")
                    ? walk({ "": j }, "")
                    : j;
            }
            // If the text is not JSON parseable, then a SyntaxError is thrown.
            throw new SyntaxError("JSON.parse");
        };
    }
}());


/***/ }),

/***/ 674:
/***/ (function(__unused_webpack_module, exports, __webpack_require__) {

"use strict";

exports.__esModule = true;
exports.logger = void 0;
__webpack_require__(658);
var SynthLogger = /** @class */ (function () {
    function SynthLogger(ipcFilename) {
        this.ipcFilename = "file:///" + ipcFilename;
        this.completed = false;
    }
    SynthLogger.prototype.begin = function () {
        this.logJson({ "control": "started" });
    };
    SynthLogger.prototype.end = function () {
        if (this.completed) {
            return;
        }
        this.logJson({ "control": "completed" });
        FLfile.write(this.ipcFilename + ".completed", "");
        this.completed = true;
    };
    SynthLogger.prototype.error = function (err) {
        this.logJson({ "error": err });
    };
    SynthLogger.prototype.log = function () {
        var args = [];
        for (var _i = 0; _i < arguments.length; _i++) {
            args[_i] = arguments[_i];
        }
        var message = args[0];
        if (typeof (args[0]) === "string") {
            message = args.join(" ");
        }
        this.logJson({ "log": message });
    };
    SynthLogger.prototype._log = function (message) {
        fl.trace(message);
        FLfile.write(this.ipcFilename, message + "\n", "append");
    };
    SynthLogger.prototype.logProperties = function (object) {
        var keys = [];
        for (k in object) {
            keys.push(k);
        }
        this.log(keys.join(", "));
    };
    SynthLogger.prototype.logJson = function (object) {
        this._log(JSON.stringify(object));
    };
    return SynthLogger;
}());
exports.logger = new SynthLogger("%ipc");
exports.default = synthrunner = function (fn) {
    // fl.showIdleMessage(false);
    try {
        exports.logger.begin();
        fn(exports.logger);
    }
    catch (err) {
        exports.logger.error(err);
    }
    exports.logger.end();
};


/***/ })

/******/ 	});
/************************************************************************/
/******/ 	// The module cache
/******/ 	var __webpack_module_cache__ = {};
/******/ 	
/******/ 	// The require function
/******/ 	function __webpack_require__(moduleId) {
/******/ 		// Check if module is in cache
/******/ 		if(__webpack_module_cache__[moduleId]) {
/******/ 			return __webpack_module_cache__[moduleId].exports;
/******/ 		}
/******/ 		// Create a new module (and put it into the cache)
/******/ 		var module = __webpack_module_cache__[moduleId] = {
/******/ 			// no module.id needed
/******/ 			// no module.loaded needed
/******/ 			exports: {}
/******/ 		};
/******/ 	
/******/ 		// Execute the module function
/******/ 		__webpack_modules__[moduleId](module, module.exports, __webpack_require__);
/******/ 	
/******/ 		// Return the exports of the module
/******/ 		return module.exports;
/******/ 	}
/******/ 	
/************************************************************************/
/******/ 	// startup
/******/ 	// Load entry module
/******/ 	__webpack_require__(766);
/******/ 	// This entry module used 'exports' so it can't be inlined
/******/ })()
;