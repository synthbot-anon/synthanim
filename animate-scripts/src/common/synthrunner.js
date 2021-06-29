import 'common/polyfill.js';


class SynthLogger {

	constructor(ipcFilename) {
		this.ipcFilename = `file:///${ipcFilename}`;
		this.completed = false;
	}

	begin() {
		this.logJson({ "control": "started" })

	}

	end() {
		if (this.completed) {
			return;
		}

		this.logJson({ "control": "completed" });
		FLfile.write(this.ipcFilename + ".completed", "");
		this.completed = true;
	}

	error(err) {
		this.logJson({ "error": err })
	}

	log(...args) {
		let message = args[0]
		if (typeof(args[0]) === "string") {
			message = args.join(" ");
		}

		this.logJson({ "log": message });
	}

	_log(message) {
		fl.trace(message);
		FLfile.write(this.ipcFilename, `${message}\n`, "append");
	}

	logProperties(object) {
		const keys = [];
		for (k in object) {
			keys.push(k);
		}
		this.log(keys.join(", "));
	}

	logJson(object) {
		this._log(JSON.stringify(object));
	}

}

export const logger = new SynthLogger("%ipc");

export default synthrunner = (fn) => {
	// fl.showIdleMessage(false);
	fl.suppressAlerts = true;

	try {
		logger.begin();
		fn(logger);

	} catch(err) {
		logger.error(err);
	}

	logger.end();
}
