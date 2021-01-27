
import youtube_dl
import wx
from language_handler import init_translation
import re

try:
	init_translation("accessible_youtube_downloader")
except:
	_ = lambda msg: msg
class Downloader:
	def __init__(self, url, path, downloading_format, monitor, monitor1, convert=False, folder=False):
		# initializing class properties
		self.url = url
		self.path = path
		self.downloading_format = downloading_format
		self.monitor = monitor 
		self.monitor1 = monitor1
		self.convert = convert
		self.folder = folder

	# progress bar updator
	def get_proper_count(self, number):
		length = len(str(number))
		if length <= 3:
			return (number, _("بايت"))
		elif length >=4 and length <7:
			return (round(number/1024, 2), _("كيلو بايت"))
		elif length >=7 and length <10:
			return (round(number/1024**2, 2), _("ميجا بايت"))
		elif length >= 10 and length < 13:
			return (round(number/1024**3, 2), _("جيجا بايت"))
		elif length >= 13:
			return (round(number/1024**4, 2), _("تيرا بايت"))

	def my_hook(self, data):
		if data['status'] == 'finished':
			return
		percent = data["_percent_str"] # extracting progress value from the data variable which is passed by the youtube downloader object
		percent = percent.replace("%", "") # remove simbles from the percentage value
		percent = percent.strip() # remove spaces
		percent = float(percent) # convert the progress value to float, the reason why we did not converted directly to integer because it is impocible to convert string containing a floating point number to integer
		percent = int(percent) # converted to integer
		total = self.get_proper_count(data["total_bytes"])
		downloaded = self.get_proper_count(data["downloaded_bytes"])
		remaining = self.get_proper_count(data["total_bytes"]-data["downloaded_bytes"])
		speed = self.get_proper_count(int(data["speed"]))
		info = [_("نسبة التنزيل: {}%").format(percent), _("حجم الملف الإجمالي: {} {}").format(total[0], total[1]), _("مقدار الحجم الذي تم تنزيله: {} {}").format(downloaded[0], downloaded[1]), _("المقدار المتبقي: {} {}").format(remaining[0], remaining[1]), _("سرعة التنزيل: {} {}").format(speed[0], speed[1])]
		# updating controls 
		wx.CallAfter(self.monitor.SetValue, percent)
		for index, value in zip(range(0, len(self.monitor1.Strings)), info):
			wx.CallAfter(self.monitor1.SetString, index, value)
	def titleCreate(self, title):
		import requests
		import bs4
		if title:
			if "&list=" in self.url:
				parts = self.url.split("&")
				for part in parts:
					if part.startswith("list="):
						self.url = f"https://www.youtube.com/playlist?{part}"
						break
			try:
				request = requests.get(self.url)
				content = request.text
				scraper = bs4.BeautifulSoup(content, "html.parser")
				title = scraper.find("title")
				title = title.getText()
				title = title.removesuffix("- YouTube")
				return title
			except:
				return
	def download(self):
		download_options = {
			'outtmpl':"{}\\%(title)s.%(ext)s".format(self.path),
			'quiet': True,
			'format': self.downloading_format,
			"youtube_include_dash_manifest": False,
			'progress_hooks': [self.my_hook],}
		if self.convert:
			download_options['postprocessors'] = [{
				"key": "FFmpegExtractAudio",
				'preferredcodec': 'mp3',
				'preferredquality': '192',
			}]
		title = self.titleCreate(self.folder)
		print(title)
		if title is not None:
			download_options['outtmpl'] = "{}\\{}\\%(title)s.%(ext)s".format(self.path, title)
			download_options["continuedl"] = True
			download_options["ignoreerrors"] = True
		with youtube_dl.YoutubeDL(download_options) as youtubeDownloader:
			youtubeDownloader.download([self.url])

def downloadAction(url, path, dlg, downloading_format, monitor, monitor1, convert=False, folder=False):
	downloader = Downloader(url, path, downloading_format, monitor, monitor1, convert=convert, folder=folder)
	try:
		wx.CallAfter(dlg.Show)
		downloader.download()
	except youtube_dl.utils.DownloadError:
		wx.MessageBox(_("لقد أدخلت رابطًأ غير صحيح. يرجى تجربة رابط آخر, أو حاول التأكد من وجود اتصال بالشبكة."), _("خطأ"), style=wx.ICON_ERROR, parent=dlg)
		wx.CallAfter(dlg.Destroy)
		return
	wx.MessageBox(_("اكتمل التنزيل بنجاح"), _("نجاح"), parent=dlg)
	wx.CallAfter(dlg.Destroy)


