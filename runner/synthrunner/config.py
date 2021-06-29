import argparse
import configparser


class SynthConfigParser(configparser.ConfigParser):
    def __init__(self, *args, **kwargs):
        super().__init__(self, *args, **kwargs)
        self.filename = None
        self.encoding = None

    def read(self, filename, encoding=None):
        assert type(filename) == str
        self.filename = filename
        self.encoding = encoding
        return super().read(filename, encoding)

    def save(self):
        assert self.filename
        with open(self.filename, "w", encoding=self.encoding) as config_file:
            super().write(config_file)


class ConfigArgAction(argparse.Action):
    def __init__(self, option_strings, dest, **kwargs):
        super().__init__(option_strings, dest, **kwargs)

    def __call__(self, parser, namespace, value, option_string=None):
        config = SynthConfigParser()
        config.read(value)
        setattr(namespace, self.dest, config)
