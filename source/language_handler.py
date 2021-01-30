from settings_handler import config_get
import gettext

def init_translation(domain):
	try:
		tr = gettext.translation(domain, localedir="languages", languages=[config_get("lang")])
	except:
		tr = gettext.translation(domain, fallback=True)
	tr.install()




