
import gettext
import ctypes
import locale


languages = ["ar", "en", "fr"]

def get_default_language():
	windll = ctypes.windll.kernel32
	lang_id = windll.GetUserDefaultUILanguage()
	try:
		language = locale.windows_locale[lang_id].split("_")[0]
		if not language in languages:
			language = "en"
	except:
		language = "en"
	return language




def init_translation(domain):
	from settings_handler import config_get
	try:
		tr = gettext.translation(domain, localedir="languages", languages=[config_get("lang")])
	except:
		tr = gettext.translation(domain, fallback=True)
	tr.install()




