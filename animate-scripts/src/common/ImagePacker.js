import { logger } from "common/synthrunner.js";

export default class ImagePacker {
	constructor(frameWidth, frameHeight) {
		this.images = [];
		this.frameWidth = frameWidth || 8192;
		this.frameHeight = frameHeight || 8192;
	}

	addImage(image, shape, width, height) {
		this.images.push(new Image(image, shape, Math.ceil(width), Math.ceil(height)))
	}

	toFrames() {
		const frames = [];
		const options = []

		this.images.forEach((image) => {
			for (let optIndex=0; optIndex<options.length; optIndex++) {
				const opt = options[optIndex];
				const position = opt.tryInserting(image);
				if (position !== null) {
					// add the image to the selected frame
					frames[opt.frame].push({image, position});

					// make sure the same space isn't used again
					const newOpts = opt.splitAround(position);
					options.splice(optIndex, 1, ...newOpts);

					return;
				}
			}

			// could not fit the image into existing options...
			// put it into a new frame
			const newFrame = new PositionOption(frames.length, 0, 0, this.frameWidth, this.frameHeight);
			let position = newFrame.tryInserting(image);
			if (position !== null) {
				logger.log("added to new frame " + image.width + ", " + image.height)
				options.push(...newFrame.splitAround(position));
				frames.push([{image, position}]);
				return;	
			}

			// it doesn't fit into a frame... force it to fit
			// const targetWidth = this.frameWidth;
			// const targetHeight = this.frameHeight;
			// const scaleWidth = image.width / targetWidth;
			// const scaleHeight = image.height / targetHeight;
			// image.requireScale(Math.max(scaleWidth, scaleHeight) * 1.1);
			// position = newFrame.tryInserting(image);
			// if (position !== null) {
			// 	logger.log("scaled to new frame " + image.width + ", " + image.height)
			// 	options.push(...newFrame.splitAround(position));
			// 	frames.push([{image, position}]);
			// 	return;	
			// }

			logger.log("failed to fit " + image.data().name)


			
		});

		return frames;
	}
}

class PositionOption {
	constructor(frame, xl, yt, xr, yb) {
		this.frame = frame;
		this.xl = xl;
		this.yt = yt;
		this.xr = xr;
		this.yb = yb;
	}

	tryInserting(image) {
		const imageXr = this.xl + image.width;
		const imageYb = this.yt + image.height;
		const hypothetical = new PositionOption(this.frame, this.xl, this.yt, imageXr, imageYb);

		if (!hypothetical.valid()) {
			logger.log("imageXr: " + imageXr);
			logger.log("imageYb: " + imageYb);
			logger.log("xl: " + this.xl);
			logger.log("yt: " + this.yt);
			return null;
		}

		if ((imageXr > this.xr) || (imageYb > this.yb)) {
			return null;
		}

		return hypothetical;
	}

	x() {
		return (this.xl + this.xr) / 2;
	}

	y() {
		return (this.yt + this.yb) / 2;
	}

	height() {
		return this.yb - this.yt;
	}

	width() {
		return this.xr - this.xl;
	}

	dump(prefix) {
		logger.log(`${prefix}: ${this.xl}, ${this.yt} to ${this.xr}, ${this.yb}`)
	}

	valid() {
		return (this.height() > 0) && (this.width() > 0);
	}

	splitAround(position) {
		const left = new PositionOption(this.frame, this.xl, position.yt, position.xl, position.yb);
		const right = new PositionOption(this.frame, position.xr, position.yt, this.xr, position.yb);
		const top = new PositionOption(this.frame, this.xl, this.yt, this.xr, position.yt);
		const bottom = new PositionOption(this.frame, this.xl, position.yb, this.xr, this.yb);
		const result = [];

		if (top.valid()) {
			result.push(top);
		}
		if (left.valid()) {
			result.push(left);
		}
		if (right.valid()) {
			result.push(right);
		}
		if (bottom.valid()) {
			result.push(bottom);
		}

		return result;
	}
}

class Image {
	constructor(data, shape, width, height) {
		this.data = data;
		this.shape = shape;
		this.width = width;
		this.height = height;
		this.applyScale = 1.0;
	}

	requireScale(factor) {
		logger.log("scaling down by " + factor);
		this.width = this.width / factor;
		this.height = this.height / factor;
		this.applyScale = this.applyScale * factor;
	}
}