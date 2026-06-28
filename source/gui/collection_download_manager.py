import os
import re
from threading import Thread

import wx
import yt_dlp as youtube_dl

from app_logger import get_logger
from download_handler.downloader import Downloader, DownloadCancelled, get_yt_dlp_options, is_browser_cookie_error
from nvda_client.client import speak
from settings_handler import config_get
from youtube_browser.search_handler import channel_videos_url
from .activity_dialog import LoadingDialog
from .download_complete_dialog import show_download_complete


logger = get_logger()


def is_collection_url(url):
	return any(part in url for part in ("list", "channel", "playlist", "/user/", "/@"))


def detect_collection_type(url):
	if "channel" in url or "/user/" in url or "/@" in url:
		return "channel"
	return "playlist"


def option_to_download_settings(option):
	if option == 0:
		return "bestvideo[ext=mp4]+bestaudio[ext=m4a]/mp4", False
	return "bestaudio[ext=m4a]", option == 2


def safe_folder_name(value):
	value = re.sub(r'[<>:"/\\|?*]', "_", value or _("downloaded videos"))
	return value.strip(" .") or _("downloaded videos")


def extract_collection_info(url, list_type="playlist", title=""):
	try:
		return extract_collection_info_with_options(url, list_type, title, use_cookies=True)
	except youtube_dl.utils.DownloadError as e:
		if not is_browser_cookie_error(e):
			logger.exception("Could not load %s for download manager. url=%s", list_type, url)
			raise
		logger.warning("Cookie-based %s load failed; retrying without cookies. url=%s error=%s", list_type, url, e)
		return extract_collection_info_with_options(url, list_type, title, use_cookies=False)


def extract_collection_info_with_options(url, list_type="playlist", title="", use_cookies=True):
	extract_url = channel_videos_url(url) if list_type == "channel" else url
	options = {
		"quiet": True,
		"no_warnings": True,
		"skip_download": True,
		"extract_flat": "in_playlist",
		"ignoreerrors": True,
	}
	options.update(get_yt_dlp_options(use_cookies=use_cookies))
	with youtube_dl.YoutubeDL(options) as ydl:
		info = ydl.extract_info(extract_url, download=False)
	collection_title = title or info.get("channel") or info.get("uploader") or info.get("title") or _("downloaded videos")
	videos = []
	for entry in info.get("entries") or []:
		video = normalize_collection_entry(entry, collection_title, url)
		if video is not None:
			videos.append(video)
	if not videos:
		raise youtube_dl.utils.DownloadError("No videos found")
	return {
		"title": collection_title,
		"type": list_type,
		"url": url,
		"videos": videos,
	}


def normalize_collection_entry(entry, collection_title, source_url):
	if not entry:
		return None
	video_id = entry.get("id")
	url = entry.get("webpage_url") or entry.get("url")
	if url and url.startswith("/"):
		url = f"https://www.youtube.com{url}"
	elif url and not url.startswith(("http://", "https://")):
		url = f"https://www.youtube.com/watch?v={url}"
	elif not url and video_id:
		url = f"https://www.youtube.com/watch?v={video_id}"
	if not url:
		return None
	title = entry.get("title") or _("unknown")
	channel_name = entry.get("channel") or entry.get("uploader") or collection_title
	channel_url = entry.get("channel_url") or entry.get("uploader_url") or source_url
	return {
		"title": title,
		"url": url,
		"channel": {
			"name": channel_name,
			"url": channel_url,
		},
	}


def collection_video_label(video):
	return video["title"]


def collection_video_state_label(video, checked):
	state = _("checked") if checked else _("not checked")
	return "{}, {}, {} {}".format(state, video["title"], _("from"), video["channel"]["name"])


def start_collection_download(parent, url, list_type=None, option=None, path=None, title=""):
	list_type = list_type or detect_collection_type(url)
	option = int(config_get("defaultformat")) if option is None else option
	path = path or config_get("path")
	loading_title = _("loading channel") if list_type == "channel" else _("loading playlist")
	try:
		collection = LoadingDialog(parent, loading_title, extract_collection_info, url, list_type, title).res
	except Exception:
		logger.exception("Could not start %s download manager. url=%s", list_type, url)
		message = _("an error occurred while trying to load the channel") if list_type == "channel" else _("an error occurred while trying to load the playlist")
		wx.MessageBox(message, _("error"), style=wx.ICON_ERROR, parent=parent)
		return
	dialog = CollectionDownloadManager(parent, collection, option, path)
	dialog.ShowModal()
	dialog.Destroy()


class CollectionDownloadManager(wx.Dialog):
	def __init__(self, parent, collection, option, path):
		super().__init__(parent, title=_("download manager"))
		self.collection = collection
		self.option = option
		self.path = path
		self.CentreOnParent()
		panel = wx.Panel(self)
		self.mode = wx.RadioBox(
			panel,
			-1,
			_("download selection"),
			choices=[_("download the whole playlist or channel"), _("choose videos to download")],
		)
		self.videosList = wx.ListCtrl(panel, -1, style=wx.LC_REPORT | wx.LC_SINGLE_SEL)
		self.videosList.InsertColumn(0, _("video"))
		self.videosList.InsertColumn(1, _("channel"))
		self.videosList.EnableCheckBoxes(True)
		self.populate_videos_list()
		self.videosList.Disable()
		toggleButton = wx.Button(panel, -1, _("check or uncheck selected video"))
		selectAllButton = wx.Button(panel, -1, _("select all"))
		clearButton = wx.Button(panel, -1, _("clear selection"))
		downloadButton = wx.Button(panel, wx.ID_OK, _("download"))
		cancelButton = wx.Button(panel, wx.ID_CANCEL, _("cancel"))
		downloadButton.SetDefault()
		self.selection_buttons = (toggleButton, selectAllButton, clearButton)
		for button in self.selection_buttons:
			button.Disable()

		summary = wx.StaticText(panel, -1, _("{}: {}. {} videos.").format(_(collection["type"]), collection["title"], len(collection["videos"])))
		sizer = wx.BoxSizer(wx.VERTICAL)
		buttonSizer = wx.BoxSizer(wx.HORIZONTAL)
		actionSizer = wx.BoxSizer(wx.HORIZONTAL)
		sizer.Add(summary, 0, wx.EXPAND)
		sizer.Add(self.mode, 0, wx.EXPAND)
		sizer.Add(self.videosList, 1, wx.EXPAND)
		for button in self.selection_buttons:
			buttonSizer.Add(button, 1, wx.EXPAND)
		sizer.Add(buttonSizer, 0, wx.EXPAND)
		actionSizer.Add(downloadButton, 1, wx.EXPAND)
		actionSizer.Add(cancelButton, 1, wx.EXPAND)
		sizer.Add(actionSizer, 0, wx.EXPAND)
		panel.SetSizer(sizer)
		self.SetSize((700, 500))

		self.mode.Bind(wx.EVT_RADIOBOX, self.onModeChanged)
		self.videosList.Bind(wx.EVT_KEY_DOWN, self.onVideoKeyDown)
		toggleButton.Bind(wx.EVT_BUTTON, self.onToggleSelected)
		selectAllButton.Bind(wx.EVT_BUTTON, self.onSelectAll)
		clearButton.Bind(wx.EVT_BUTTON, self.onClearSelection)
		downloadButton.Bind(wx.EVT_BUTTON, self.onDownload)
		cancelButton.Bind(wx.EVT_BUTTON, lambda event: self.EndModal(wx.ID_CANCEL))

	def populate_videos_list(self):
		for index, video in enumerate(self.collection["videos"]):
			self.videosList.InsertItem(index, collection_video_label(video))
			self.videosList.SetItem(index, 1, video["channel"]["name"])
		self.videosList.SetColumnWidth(0, 420)
		self.videosList.SetColumnWidth(1, 220)

	def selected_index(self):
		return self.videosList.GetFirstSelected()

	def checked_label(self, index):
		return collection_video_state_label(self.collection["videos"][index], self.videosList.IsItemChecked(index))

	def onModeChanged(self, event):
		enabled = self.mode.Selection == 1
		self.videosList.Enable(enabled)
		for button in self.selection_buttons:
			button.Enable(enabled)
		if enabled and self.selected_index() == -1 and self.videosList.GetItemCount():
			self.videosList.Select(0)

	def onVideoKeyDown(self, event):
		if event.KeyCode == wx.WXK_SPACE:
			self.toggle_selected_video()
			return
		event.Skip()

	def onToggleSelected(self, event):
		self.toggle_selected_video()
		self.videosList.SetFocus()

	def toggle_selected_video(self):
		index = self.selected_index()
		if index == -1:
			return
		self.videosList.CheckItem(index, not self.videosList.IsItemChecked(index))
		self.videosList.Select(index)
		speak(self.checked_label(index))

	def onSelectAll(self, event):
		for index in range(self.videosList.GetItemCount()):
			self.videosList.CheckItem(index, True)
		speak(_("all videos selected"))
		self.videosList.SetFocus()

	def onClearSelection(self, event):
		for index in range(self.videosList.GetItemCount()):
			self.videosList.CheckItem(index, False)
		speak(_("selection cleared"))
		self.videosList.SetFocus()

	def selected_videos(self):
		if self.mode.Selection == 0:
			return self.collection["videos"]
		return [
			self.collection["videos"][index]
			for index in range(self.videosList.GetItemCount())
			if self.videosList.IsItemChecked(index)
		]

	def onDownload(self, event):
		videos = self.selected_videos()
		if not videos:
			wx.MessageBox(_("please select at least one video to download."), _("error"), style=wx.ICON_ERROR, parent=self)
			self.videosList.SetFocus()
			return
		format, convert = option_to_download_settings(self.option)
		download_path = os.path.join(self.path, safe_folder_name(self.collection["title"]))
		progress = CollectionDownloadProgress(self.GetParent(), self.collection, len(videos), download_path)
		job = CollectionDownloadJob(videos, download_path, format, convert, progress)
		Thread(target=job.run, daemon=True).start()
		self.EndModal(wx.ID_OK)


class CollectionDownloadProgress(wx.Frame):
	def __init__(self, parent, collection, total, output_folder):
		super().__init__(parent, title=_("downloading {} - {}").format(_(collection["type"]), collection["title"]))
		self.collection = collection
		self.total = total
		self.output_folder = output_folder
		self.completed = 0
		self.failed = 0
		self.cancelled = False
		self.downloader = None
		self.Centre()
		panel = wx.Panel(self)
		self.status = wx.Choice(panel, -1, choices=[
			_("{}: {}").format(_(collection["type"]), collection["title"]),
			_("current video: {}").format(_("waiting")),
			_("completed videos: {} of {}").format(0, total),
			_("download percentage: {}%").format(0),
			_("total file size: {} {}"),
			_("downloaded size: {} {}"),
			_("remaining file size: {} {}"),
			_("downloading speed: {} {}"),
		])
		self.status.progress_offset = 3
		self.status.Selection = 0
		self.overallGauge = wx.Gauge(panel, -1, range=max(1, total))
		self.gaugeProgress = wx.Gauge(panel, -1, range=100)
		completedLabel = wx.StaticText(panel, -1, _("completed videos"))
		self.completedList = wx.ListBox(panel, -1)
		self.stopButton = wx.Button(panel, -1, _("stop download"))

		sizer = wx.BoxSizer(wx.VERTICAL)
		sizer.Add(self.status, 0, wx.EXPAND)
		sizer.Add(self.overallGauge, 0, wx.EXPAND)
		sizer.Add(self.gaugeProgress, 0, wx.EXPAND)
		sizer.Add(completedLabel, 0, wx.EXPAND)
		sizer.Add(self.completedList, 1, wx.EXPAND)
		sizer.Add(self.stopButton, 0, wx.EXPAND)
		panel.SetSizer(sizer)
		self.SetSize((700, 500))
		self.stopButton.Bind(wx.EVT_BUTTON, self.onStop)
		self.Bind(wx.EVT_CLOSE, self.onClose)
		self.Bind(wx.EVT_CHAR_HOOK, self.onHook)

	def set_downloader(self, downloader):
		self.downloader = downloader

	def set_current_video(self, index, title):
		self.gaugeProgress.SetValue(0)
		for progress_index, value in enumerate([
			_("download percentage: {}%").format(0),
			_("total file size: {} {}"),
			_("downloaded size: {} {}"),
			_("remaining file size: {} {}"),
			_("downloading speed: {} {}"),
		], start=self.status.progress_offset):
			self.status.SetString(progress_index, value)
		self.status.SetString(1, _("current video: {} of {} - {}").format(index, self.total, title))
		self.status.Selection = 1

	def add_completed_video(self, title):
		self.completed += 1
		self.overallGauge.SetValue(self.completed+self.failed)
		self.status.SetString(2, _("completed videos: {} of {}").format(self.completed, self.total))
		self.completedList.Append(_("completed: {}").format(title))

	def add_failed_video(self, title):
		self.failed += 1
		self.overallGauge.SetValue(self.completed+self.failed)
		self.completedList.Append(_("failed: {}").format(title))

	def downloaded_file_for(self, downloader):
		if downloader.last_file and os.path.exists(downloader.last_file):
			return downloader.last_file
		path = downloader.find_latest_downloaded_file()
		if path and os.path.exists(path):
			downloader.last_file = path
			return path
		return None

	def finish(self):
		self.stopButton.Disable()
		parent = self.GetParent()
		if self.cancelled:
			self.status.SetString(1, _("current video: download stopped"))
			self.Destroy()
		else:
			self.status.SetString(1, _("current video: finished"))
			self.Hide()
			show_download_complete(parent, folder_path=self.output_folder)
			self.Destroy()

	def onStop(self, event):
		self.stop_download()

	def stop_download(self):
		self.cancelled = True
		self.stopButton.Disable()
		if self.downloader is not None:
			self.downloader.cancel()
		self.Hide()

	def onClose(self, event):
		if self.stopButton.Enabled:
			message = wx.MessageBox(_("There is an active download. Do you want to cancel it?"), _("Exit"), style=wx.YES_NO, parent=self)
			if message != wx.YES:
				return
			self.stop_download()
			return
		self.Destroy()

	def onHook(self, event):
		if event.KeyCode == wx.WXK_ESCAPE:
			if self.stopButton.Enabled:
				self.stop_download()
			else:
				self.Destroy()
			return
		event.Skip()


class CollectionDownloadJob:
	def __init__(self, videos, path, downloading_format, convert, progress):
		self.videos = videos
		self.path = path
		self.downloading_format = downloading_format
		self.convert = convert
		self.progress = progress

	def run(self):
		os.makedirs(self.path, exist_ok=True)
		wx.CallAfter(self.progress.Show)
		for index, video in enumerate(self.videos, start=1):
			if self.progress.cancelled:
				break
			wx.CallAfter(self.progress.set_current_video, index, video["title"])
			downloader = Downloader(video["url"], self.path, self.downloading_format, self.progress.gaugeProgress, self.progress.status, convert=self.convert, folder=False)
			wx.CallAfter(self.progress.set_downloader, downloader)
			try:
				logger.info("Downloading collection item. index=%s title=%s url=%s", index, video["title"], video["url"])
				downloader.download_with_cookie_fallback()
			except DownloadCancelled:
				logger.info("Collection download cancelled. title=%s url=%s", video["title"], video["url"])
				self.progress.cancelled = True
				break
			except youtube_dl.utils.DownloadError:
				if self.progress.downloaded_file_for(downloader):
					logger.warning("Collection item raised an error after producing a file; counting as completed. title=%s url=%s", video["title"], video["url"])
					wx.CallAfter(self.progress.add_completed_video, video["title"])
				else:
					logger.exception("Collection item download failed. title=%s url=%s", video["title"], video["url"])
					wx.CallAfter(self.progress.add_failed_video, video["title"])
				continue
			wx.CallAfter(self.progress.add_completed_video, video["title"])
		wx.CallAfter(self.progress.finish)
