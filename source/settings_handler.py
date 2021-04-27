import configparser
import os
from language_handler import get_default_language


settings_path = os.path.join(os.getenv("appdata"), "accessible youtube downloader pro")

defaults = {
	"path": f"{os.getenv('USERPROFILE')}\\downloads\\accessible youtube downloader",
	"defaultaudio": 0,
	"lang": get_default_language(),
	"autodetect": True,
	"autoload": True,
	"seek": 5,
	"conversion": 1,
	"repeatetracks":False,
	"defaultformat": 0
}

def config_initialization():
	try:
		os.mkdir(settings_path)
	except FileExistsError:
		pass
	if not os.path.exists(os.path.join(settings_path, "settings.ini")):
		config = configparser.ConfigParser()
		config.add_section("settings")
		for key, value in defaults.items():
			config["settings"][key] = str(value)
		with open(os.path.join(settings_path, "settings.ini"), "w") as file:
			config.write(file)

def string_to_bool(string):
	if string == "True":
		return True
	elif string == "False":
		return False
	else:
		return string


def config_get(string):
	config = configparser.ConfigParser()
	config.read(os.path.join(settings_path, "settings.ini"))
	try:
		value = config["settings"][string]
		return string_to_bool(value)
	except KeyError:
		config_set(string, defaults[string])
		return defaults[string]


def config_set(key, value):
	config = configparser.ConfigParser()
	config.read(os.path.join(settings_path, "settings.ini"))
	config["settings"][key] = str(value)
	with open(os.path.join(settings_path, "settings.ini"), "w") as file:
		config.write(file)

