import { logger } from "common/synthrunner.js";

export default class ImagePacker {
	constructor(frameWidth, frameHeight) {
		this.images = [];
		this.frameWidth = frameWidth || 8192;
		this.frameHeight = frameHeight || 8192;
	}

	addImage(image, width, height) {
		this.images.push(new Image(image, Math.ceil(width), Math.ceil(height)))
	}

	toFrames() {
		const frames = [];
		const options = []

		this.images.forEach((image) => {
			for (let optIndex=0; optIndex<options.length; optIndex++) {
				const opt = options[optIndex];
				const position = opt.tryInserting(image);
				if (position) {
					// add the image to the selected frame
					frames[opt.frame].push({image, position});

					// make sure the same space isn't used again
					const newOpts = opt.splitAround(position);
					options.splice(optIndex, 1, ...newOpts);

					insertedImage = true;
					return;
				}
			}

			// could not fit the image into existing options...
			// put it into a new frame
			const newFrame = new PositionOption(frames.length, 0, 0, 8192, 8192);
			const position = newFrame.tryInserting(image);
			frames.push([{image, position}]);
			options.push(...newFrame.splitAround(position));
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
		if (image.height > (this.yb - this.yt)) {
			return null;
		}
		
		if (image.width > (this.xr - this.xl)) {
			return null;
		}

		const imageXr = this.xl + image.width;
		const imageYb = this.yt + image.height;
		return new PositionOption(this.frame, this.xl, this.yt, imageXr, imageYb);

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

	splitAround(position) {
		const left = new PositionOption(this.frame, this.xl, this.yt, position.xl, this.yb);
		const right = new PositionOption(this.frame, position.xr, this.yt, this.xr, this.yb);
		const top = new PositionOption(this.frame, this.xl, this.yt, this.xr, position.yt);
		const bottom = new PositionOption(this.frame, this.xl, position.yb, this.xr, this.yb);

		const result = [];
		if (left.height() && this.width()) {
			result.push(left);
		}
		if (right.height() && right.width()) {
			result.push(right);
		}
		if (top.height() && top.width()) {
			result.push(top);
		}
		if (bottom.height() && bottom.width()) {
			result.push(bottom);
		}

		return result;
	}
}

class Image {
	constructor(data, width, height) {
		this.data = data;
		this.width = width;
		this.height = height;
	}
}