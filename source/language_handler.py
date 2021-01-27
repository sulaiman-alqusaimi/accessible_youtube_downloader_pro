from settings_handler import config_get
import gettext

def init_translation(domain):
	tr = gettext.translation(domain, localedir="languages", languages=[config_get("lang")])
	tr.install()




