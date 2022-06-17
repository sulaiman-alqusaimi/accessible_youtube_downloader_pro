import re
from threading import Thread
from settings_handler import config_get
from download_handler.downloader import downloadAction
import json
import requests
import wx
import application
import pafy




resolution = "640x360"
def get_audio_stream(url):
	media = pafy.new(url)
	streams = media.audiostreams
	for stream in streams[::-1]:
		if stream.extension == "webm":
			break
	else:
		stream = media.getbestaudio()
	return stream

def get_video_stream(url):
	media = pafy.new(url)
	for stream in media.streams:
		if stream.extension == "mp4" and stream.resolution == resolution:
			break
	else:
		stream = media.getbest()
	return stream

def time_formatting( t):
	t = t.split(":")
	t = [int(i) for i in t]
	t.pop(0) if t[0] == 0 else None
	def minute(m):
		if m == 1:
			return _("دقيقة واحدة")
		elif m == 2:
			return _("دقيقتان")
		elif m >=3 and m <=10:
			return _("{} دقائق").format(m)
		else:
			return _("{} دقيقة").format(m)
	def second(s):
		if s == 1:
			return _("ثانية")
		elif s == 2:
			return _("ثانيتين")
		elif s >= 3 and s <= 10:
			return _("{} ثواني").format(s)
		else:
			return _("{} ثانية").format(s)
	def hour(h):
		if h == 1:
			return _("ساعة")
		elif h == 2:
			return _("ساعتان")
		elif h >= 3 and h <=10:
			return _("{} ساعات").format(h)
		else:
			return _("{} ساعة").format(h)
	if len(t) == 1:
		return second(t[0])
	elif len(t) == 2:
		return _("{} و{}").format(minute(t[0]), second(t[1]))
	elif len(t) == 3:
		return _("{} و{} و{}").format(hour(t[0]), minute(t[1]), second(t[2]))

def youtube_regexp(string):
	pattern = re.compile("^((?:https?:)?\/\/)?((?:www|m)\.)?((?:youtube\.com|youtu.be))(\/(?:[\w\-]+\?v=|embed\/|v\/)?)([\w\-]+)(\S+)?$") # youtube links regular expression pattern
	return pattern.search(string)

def direct_download(option, url, dlg, download_type="video", path=config_get("path")):
	if option == 0:
		format = "bestvideo[ext=mp4]+bestaudio[ext=m4a]/mp4"
	else:
		format = "bestaudio[ext=m4a]"
	convert = True if option == 2 else False
	folder = False if download_type == "video" else True
	trd = Thread(target=downloadAction, args=[url, path, dlg, format, dlg.gaugeProgress, dlg.textProgress, convert, folder])
	trd.start()

def check_for_updates(quiet=False):
	url = "https://raw.githubusercontent.com/sulaiman-alqusaimi/accessible_youtube_downloader_pro/master/update_info.json"
	try:
		r = requests.get(url)
		if r.status_code != 200:
			wx.MessageBox(
				_("حدث خطأ ما أثناء الاتصال بخدمة العثور على التحديثات. تأكد من وجود اتصال مستقر بالإنترنت ثم عاود المحاولة"), 
				_("خطأ"), 
				parent=wx.GetApp().GetTopWindow(), style=wx.ICON_ERROR
			) if not quiet else None
			return
		info = r.json()
		if application.version != info["version"]:
			message = wx.MessageBox(_("هناك تحديث جديد متوفر. هل ترغب في تنزيله الآن؟"), _("تحديث جديد"), parent=wx.GetApp().GetTopWindow(), style=wx.YES_NO)
			url = info["url"]
			if message == wx.YES:
				from gui.update_dialog import UpdateDialog
				wx.CallAfter(UpdateDialog, wx.GetApp().GetTopWindow(), url)
			return
		wx.MessageBox(_("أنت تعمل الآن على آخر تحديث متوفر من التطبيق"), _("لا يوجد تحديث"), parent=wx.GetApp().GetTopWindow()) if not quiet else None
	except requests.ConnectionError:
		wx.MessageBox(
			_("حدث خطأ ما أثناء الاتصال بخدمة العثور على التحديثات. تأكد من وجود اتصال مستقر بالإنترنت ثم عاود المحاولة"), 
			_("خطأ"), 
			parent=wx.GetApp().GetTopWindow(), style=wx.ICON_ERROR
		) if not quiet else None
