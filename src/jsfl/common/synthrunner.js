import 'common/polyfill.js';

class SynthLogger {

	constructor(ipcFilename) {
		this.ipcFilename = `file:///${ipcFilename}`;
		this.completed = false;
	}

	begin() {
		this.logJson({ "status": "started" })

	}

	end() {
		if (this.completed) {
			return;
		}

		this.logJson({ "status": "completed" });
		FLfile.write(this.ipcFilename + ".completed", "");
		this.completed = true;
	}

	error(err) {
		this.logJson({ "error": err })
	}

	status(object) {
		this.logJson({ "status": object });
	}

	log(...message) {
		const output = message.join(' ');

		fl.trace(output);
		fl.trace(this.ipcFilename);
		FLfile.write(this.ipcFilename, output, "append");
		FLfile.write(this.ipcFilename, "\n", "append");
	}

	logProperties(object) {
		const keys = [];
		for (k in object) {
			keys.push(k);
		}
		this.log(keys.join(", "));
	}

	logJson(object) {
		this.log(JSON.stringify(object));
	}

}

export default synthrunner = (fn) => {
	let logger = new SynthLogger("%ipc");

	try {
		logger.begin();
		fn(logger);

	} catch(err) {
		logger.error(err);
	}

	logger.end();
}
