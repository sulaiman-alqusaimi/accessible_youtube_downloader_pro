
import yt_dlp as youtube_dl

import wx
import re
import os
import time
from settings_handler import config_get
from app_logger import get_logger


logger = get_logger()


class DownloadCancelled(Exception):
	pass


def get_cookies_from_browser():
	browser = config_get("cookiesfrombrowser")
	if browser == "none":
		return None
	return (browser, None, None, None)


def get_yt_dlp_options(use_cookies=True):
	options = {}
	cookiesfrombrowser = get_cookies_from_browser() if use_cookies else None
	if cookiesfrombrowser:
		options["cookiesfrombrowser"] = cookiesfrombrowser
		logger.info("Using browser cookies. browser=%s", cookiesfrombrowser[0])
	return options


def is_browser_cookie_error(error):
	message = str(error).lower()
	return any(part in message for part in (
		"cookie",
		"cookies",
		"dpapi",
		"decrypt",
		"could not copy",
		"database is locked",
		"unable to open database file",
	))


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
		self.cancelled = False
		self.last_file = None
		self.started_at = None

	def cancel(self):
		logger.info("Download cancellation requested. url=%s", self.url)
		self.cancelled = True

	def remember_file(self, path):
		if path and os.path.exists(path):
			self.last_file = path

	def get_hook_file(self, data):
		if isinstance(data, str):
			return data
		if not isinstance(data, dict):
			return None
		info = data.get("info_dict") or {}
		return data.get("filepath") or data.get("filename") or info.get("filepath") or info.get("_filename")

	def after_move_hook(self, data):
		self.remember_file(self.get_hook_file(data))

	def postprocessor_hook(self, data):
		if isinstance(data, dict) and data.get("status") not in (None, "finished"):
			return
		self.remember_file(self.get_hook_file(data))

	def find_latest_downloaded_file(self):
		if not os.path.isdir(self.path):
			return None
		latest_file = None
		latest_time = 0
		for root, dirs, files in os.walk(self.path):
			for filename in files:
				path = os.path.join(root, filename)
				try:
					modified = os.path.getmtime(path)
				except OSError:
					continue
				if self.started_at is not None and modified < self.started_at-2:
					continue
				if modified > latest_time:
					latest_time = modified
					latest_file = path
		return latest_file

	# progress bar updator
	def get_proper_count(self, number):
		length = len(str(int(number)))
		if length <= 3:
			return (number, _("bytes"))
		elif length >=4 and length <7:
			return (round(number/1024, 2), _("kilobytes"))
		elif length >=7 and length <10:
			return (round(number/1024**2, 2), _("megabytes"))
		elif length >= 10 and length < 13:
			return (round(number/1024**3, 2), _("gigabytes"))
		elif length >= 13:
			return (round(number/1024**4, 2), _("terabytes"))
	def get_quality(self):
		qualities = {
			0: '96',
			1: '128',
			2: '192'
		}
		return qualities[int(config_get("conversion"))]
	def my_hook(self, data):
		if self.cancelled:
			raise DownloadCancelled()
		if data['status'] == 'finished':
			self.remember_file(data.get("filename"))
			return
		total_bytes = data.get("total_bytes", data.get("total_bytes_estimate", 0)) or 0
		if not total_bytes:
			return
		percent = (data["downloaded_bytes"] / total_bytes) * 100
		#percent = percent.replace("%", "") # remove simbles from the percentage value
		#percent = percent.strip() # remove spaces
		#percent = float(percent) # convert the progress value to float, the reason why we did not converted directly to integer because it is impocible to convert string containing a floating point number to integer
		percent = int(percent) # converted to integer
		total = total_bytes
		logger.debug("Download progress total bytes: %s", total)
		total = self.get_proper_count(total)
		downloaded = self.get_proper_count(data["downloaded_bytes"])
		remaining = self.get_proper_count(total_bytes-data["downloaded_bytes"])
		speed = data['speed'] if data['speed'] else 0
		speed = self.get_proper_count(int(speed))
		info = [_("download percentage: {}%").format(percent), _("total file size: {} {}").format(total[0], total[1]), _("downloaded size: {} {}").format(downloaded[0], downloaded[1]), _("remaining file size: {} {}").format(remaining[0], remaining[1]), _("downloading speed: {} {}").format(speed[0], speed[1])]
		# updating controls 
		wx.CallAfter(self.monitor.SetValue, percent)
		offset = getattr(self.monitor1, "progress_offset", 0)
		for index, value in zip(range(offset, len(self.monitor1.Strings)), info):
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
	def download(self, use_cookies=True):
		logger.info(
			"Starting download. use_cookies=%s format=%s convert=%s folder=%s path=%s url=%s",
			use_cookies,
			self.downloading_format,
			self.convert,
			self.folder,
			self.path,
			self.url,
		)
		self.started_at = time.time()
		download_options = {
			'outtmpl':"{}\\%(title)s.%(ext)s".format(self.path),
			'quiet': True,
			'format': self.downloading_format,
			'noplaylist': not self.folder,
			"continuedl": True,
			"youtube_include_dash_manifest": False,
			'progress_hooks': [self.my_hook],
			'postprocessor_hooks': [self.postprocessor_hook],
			'post_hooks': [self.after_move_hook],}
		download_options.update(get_yt_dlp_options(use_cookies=use_cookies))
		if self.convert:
			download_options['postprocessors'] = [{
				"key": "FFmpegExtractAudio",
				'preferredcodec': 'mp3',
				'preferredquality': self.get_quality(),
			}]
		title = self.titleCreate(self.folder)
		if title is not None:
			download_options['outtmpl'] = "{}\\{}\\%(title)s.%(ext)s".format(self.path, title)
			#download_options["ignoreerrors"] = True
		with youtube_dl.YoutubeDL(download_options) as youtubeDownloader:
			youtubeDownloader.download([self.url])
		if not self.last_file or not os.path.exists(self.last_file):
			self.last_file = self.find_latest_downloaded_file()
		logger.info("Download finished. url=%s", self.url)
		return self.last_file

	def download_with_cookie_fallback(self):
		try:
			self.download(use_cookies=True)
		except youtube_dl.utils.DownloadError as e:
			if not is_browser_cookie_error(e):
				logger.exception("Download failed. url=%s", self.url)
				raise
			logger.warning("Cookie-based download failed; retrying without cookies. url=%s error=%s", self.url, e)
			self.download(use_cookies=False)

def downloadAction(url, path, dlg, downloading_format, monitor, monitor1, convert=False, folder=False):
	downloader = Downloader(url, path, downloading_format, monitor, monitor1, convert=convert, folder=folder)
	if hasattr(dlg, "set_downloader"):
		wx.CallAfter(dlg.set_downloader, downloader)
	wx.CallAfter(dlg.Show)
	def attempt(at):
		try:
			logger.info("Download attempt %s started. url=%s", at + 1, url)
			downloader.download_with_cookie_fallback()
			return True
		except DownloadCancelled:
			logger.info("Download cancelled. url=%s", url)
			if hasattr(dlg, "set_cancelled"):
				wx.CallAfter(dlg.set_cancelled)
			return False
		except youtube_dl.utils.DownloadError:
			if at < 3:
				logger.warning("Download attempt %s failed; retrying. url=%s", at + 1, url)
				return attempt(at+1)
			else:
				logger.exception("Download failed after retries. url=%s", url)
				wx.MessageBox(_("either an internet connection occured or you have enterd an invalid YouTube url. please check that out and try again."), _("error"), style=wx.ICON_ERROR, parent=dlg)
				wx.CallAfter(dlg.Destroy)
	if attempt(0):
		def complete():
			parent = dlg.GetParent() if dlg is not None else wx.GetApp().GetTopWindow()
			if dlg is not None:
				dlg.Destroy()
			from gui.download_complete_dialog import show_download_complete
			show_download_complete(parent, file_path=downloader.last_file, folder_path=path)
		wx.CallAfter(complete)


