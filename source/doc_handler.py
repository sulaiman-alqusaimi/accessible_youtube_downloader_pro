from settings_handler import config_get
import os
import application
available_languages = os.listdir()

def documentation_get():
	lang = config_get("lang")
	if not lang in available_languages:
		lang = "ar"
	path = os.path.join(os.getcwd(), f"docs\\{lang}\\guide.txt")
	if not os.path.exists(path):
		return

	with open(path, "r", encoding="utf-8") as file:
		namespace = {"name": application.name, "version": application.version, "author": application.author}
		return file.read().format(**namespace)
