
class SynthLogger {

	constructor() {
		this.optionalFile = null;
	}

	trace(...message) {
		const output = message.join(' ');
		fl.trace(output);
		if (this.optionalFile) {
			FLfile.write(this.optionalFile, output, "append");
		}
	}

	traceProperties(object) {
		const keys = [];
		for (k in object) {
			keys.push(k);
		}
		this.trace(keys.join(", "));
	}

	tee(filename) {
		this.optionalFile = `file:///${filename}`;
	}

	clear(filename) {
		FLfile.remove(`file:///${filename}`);
	}
}

export default new SynthLogger();