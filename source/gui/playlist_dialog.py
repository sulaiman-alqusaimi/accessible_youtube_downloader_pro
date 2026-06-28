import wx
from youtube_browser.search_handler import ChannelResult, PlaylistResult
from utiles import direct_download, get_audio_stream, get_video_stream
from media_player.media_gui import MediaGui, get_active_media_window
from nvda_client.client import speak
import pyperclip
from gui.download_progress import DownloadProgress
from settings_handler import config_get
import webbrowser
from threading import Thread
import os
from .activity_dialog import LoadingDialog
import application
from app_logger import get_logger


logger = get_logger()

class PlaylistDialog(wx.Dialog):
	def __init__(self, parent, url, list_type="playlist", title=""):
		logger.info("Opening %s dialog. url=%s", list_type, url)
		super().__init__(parent, title=application.name)
		self.CenterOnParent()
		self.url = url
		self.list_type = list_type
		self.initial_title = title
		self.Maximize(True)
		p = wx.Panel(self)
		l1 = wx.StaticText(p, -1, _("videos list"))
		self.videosBox = wx.ListBox(p, -1)
		self.playButton = wx.Button(p, -1, _("play"), name="control")
		self.downloadButton = wx.Button(p, -1, _("download"), name="control")
		backButton = wx.Button(p, -1, _("back"), name="control")
		self.contextSetup()

		hotkeys = wx.AcceleratorTable([
				(0, wx.WXK_RETURN, self.audioPlayItemId),
				(wx.ACCEL_CTRL, wx.WXK_RETURN, self.videoPlayItemId),
				(wx.ACCEL_CTRL, ord("D"), self.directDownloadId),
			(wx.ACCEL_CTRL, ord("L"), self.copyItemId),
			])
		self.videosBox.SetAcceleratorTable(hotkeys)

		sizer = wx.BoxSizer(wx.VERTICAL)
		sizer.Add(l1, 1)
		sizer.Add(self.videosBox, 1, wx.EXPAND)
		ctrlSizer = wx.BoxSizer(wx.HORIZONTAL)
		for control in p.GetChildren():
			if control.Name == "control":
				ctrlSizer.Add(control, 1)
		sizer.Add(ctrlSizer)
		p.SetSizer(sizer)
		self.videosBox.Bind(wx.EVT_LISTBOX, self.onListBox)
		self.playButton.Bind(wx.EVT_BUTTON, lambda e: self.playVideo())
		self.downloadButton.Bind(wx.EVT_BUTTON, self.onDownload)
		backButton.Bind(wx.EVT_BUTTON, lambda e: self.back())
		self.Bind(wx.EVT_CHAR_HOOK, self.onHook)
		self.Bind(wx.EVT_CLOSE, lambda e: wx.Exit())
		try:
			if self.list_type == "channel":
				self.result = LoadingDialog(self.Parent, _("loading channel"), ChannelResult, self.url, self.initial_title).res
				self.title = self.result.title
			else:
				self.result = LoadingDialog(self.Parent, _("loading playlist"), PlaylistResult, self.url, self.initial_title).res
				self.title = self.result.title or self.initial_title or _("playlist")
			self.SetTitle(f"{application.name} - {self.title}")
			self.videosBox.Set(self.result.get_display_titles())
		except Exception:
			logger.exception("Could not open %s. url=%s", self.list_type, self.url)
			message = _("an error occurred while trying to load the channel") if self.list_type == "channel" else _("an error occurred while trying to load the playlist")
			wx.MessageBox(message, _("error"), style=wx.ICON_ERROR, parent=self)
			self.Destroy()
			return
		self.Parent.Hide()
		self.Show()
		if self.videosBox.Count:
			self.videosBox.Selection = 0
			self.togleChannelActions()
	def contextSetup(self):
		self.contextMenu = wx.Menu()
		videoPlayItem = self.contextMenu.Append(-1, _("play"))
		self.videoPlayItemId = videoPlayItem.GetId()
		audioPlayItem = self.contextMenu.Append(-1, _("play as audio track"))
		self.audioPlayItemId = audioPlayItem.GetId()
		self.downloadMenu = wx.Menu()
		videoItem = self.downloadMenu.Append(-1, _("Video"))
		audioMenu = wx.Menu()
		m4aItem = audioMenu.Append(-1, "m4a")
		mp3Item = audioMenu.Append(-1, "mp3")
		self.downloadMenu.AppendSubMenu(audioMenu, _("audio"))
		self.downloadId = self.contextMenu.AppendSubMenu(self.downloadMenu, _("download")).GetId()
		directDownloadItem = self.contextMenu.Append(-1, _("direct download...\tctrl+d"))
		self.directDownloadId = directDownloadItem.GetId()
		openChannelMenu = wx.Menu()
		openChannelInAppItem = openChannelMenu.Append(-1, _("open in app"))
		self.openChannelInAppItemId = openChannelInAppItem.GetId()
		openChannelInBrowserItem = openChannelMenu.Append(-1, _("open in browser"))
		self.openChannelInBrowserItemId = openChannelInBrowserItem.GetId()
		self.contextMenu.AppendSubMenu(openChannelMenu, _("navigate to the channel"))
		downloadChannelItem = self.contextMenu.Append(-1, _("download channel"))
		self.downloadChannelItemId = downloadChannelItem.GetId()
		copyItem = self.contextMenu.Append(-1, _("copy video link"))
		self.copyItemId = copyItem.GetId()
		webbrowserItem = self.contextMenu.Append(-1, _("open in browser"))
		def popup():
			if self.result.videos:
				self.videosBox.PopupMenu(self.contextMenu)
		self.videosBox.Bind(wx.EVT_CONTEXT_MENU, lambda event: popup())
		# binding item events 
		self.videosBox.Bind(wx.EVT_MENU, lambda e: self.playVideo(), id=self.videoPlayItemId)
		self.videosBox.Bind(wx.EVT_MENU, lambda e: self.playAudio(), id=self.audioPlayItemId)
		self.videosBox.Bind(wx.EVT_MENU, self.onVideoDownload, videoItem)
		self.Bind(wx.EVT_MENU, self.onM4aDownload, m4aItem)
		self.Bind(wx.EVT_MENU, self.onMp3Download, mp3Item)
		self.videosBox.Bind(wx.EVT_MENU, lambda e: self.directDownload(), id=self.directDownloadId)
		self.videosBox.Bind(wx.EVT_MENU, self.onCopy, id=self.copyItemId)
		self.videosBox.Bind(wx.EVT_MENU, self.onOpenChannel, openChannelInAppItem)
		self.videosBox.Bind(wx.EVT_MENU, self.onOpenChannelInBrowser, openChannelInBrowserItem)
		self.videosBox.Bind(wx.EVT_MENU, self.onDownloadChannel, downloadChannelItem)
		self.Bind(wx.EVT_MENU, self.onOpenInBrowser, webbrowserItem)

	def onOpenInBrowser(self, event):
		n = self.videosBox.Selection
		webbrowser.open(self.result.get_url(n))

	def onCopy(self, event):
		n = self.videosBox.Selection
		pyperclip.copy(self.result.get_url(n))
		wx.MessageBox(_("video URL has been copyed successfully."), _("done"), parent=self)

	def onOpenChannel(self, event):
		n = self.videosBox.Selection
		channel = self.result.videos[n]['channel']
		PlaylistDialog(self, channel['url'], "channel", channel['name'])

	def onOpenChannelInBrowser(self, event):
		n = self.videosBox.Selection
		webbrowser.open(self.result.videos[n]['channel']['url'])

	def onDownloadChannel(self, event):
		n = self.videosBox.Selection
		title = self.result.videos[n]["channel"]['name']
		url = self.result.videos[n]["channel"]['url']
		download_type = "channel"
		logger.info("Downloading playlist video channel. title=%s url=%s", title, url)
		dlg = DownloadProgress(wx.GetApp().GetTopWindow(), title)
		direct_download(int(config_get('defaultformat')), url, dlg, download_type)

	def playVideo(self):
		n = self.videosBox.Selection
		url = self.result.get_url(n)

		title = self.result.get_title(n)

		logger.info("Playing playlist video. title=%s url=%s", title, url)
		stream = LoadingDialog(self, _("playing"), get_video_stream, url).res
		gui = MediaGui(self, title, stream, url, True, self.result, history_data=self.result.get_history_data(n))
		gui.path = os.path.join(gui.path, self.title)
		self.Hide()

	def playAudio(self):
		n = self.videosBox.Selection
		url = self.result.get_url(n)

		title = self.result.get_title(n)

		logger.info("Playing playlist audio. title=%s url=%s", title, url)
		stream = LoadingDialog(self, _("playing"), get_audio_stream, url).res

		gui = MediaGui(self, title, stream, url, audio_mode=True, results=self.result, history_data=self.result.get_history_data(n))
		gui.path = os.path.join(gui.path, self.title)
		self.Hide()


	def onListBox(self, event):
		n = self.videosBox.Selection
		self.togleChannelActions()
		if n == self.videosBox.Count-1:
			def load():
				try:
					if self.result.next():
						titles = self.result.get_new_titles()
						wx.CallAfter(self.videosBox.Append, titles)
						speak(_("more videos loaded"))
					else:
						speak(_("no more videos"))
				except Exception:
					logger.exception("Could not load more playlist videos. url=%s", self.url)
					speak(_("could not load more videos"))
			Thread(target=load).start()

	def togleChannelActions(self):
		n = self.videosBox.Selection
		if n < 0 or n >= len(self.result.videos):
			enabled = False
		else:
			enabled = bool(self.result.videos[n]["channel"].get("url"))
		self.contextMenu.Enable(self.openChannelInAppItemId, enabled)
		self.contextMenu.Enable(self.openChannelInBrowserItemId, enabled)
		self.contextMenu.Enable(self.downloadChannelItemId, enabled)

	def onVideoDownload(self, event):
		n = self.videosBox.Selection
		url = self.result.get_url(n)
		title = self.result.get_title(n)
		logger.info("Downloading playlist video as video. title=%s url=%s", title, url)
		dlg = DownloadProgress(self.Parent, title)
		direct_download(0, url, dlg, "video", os.path.join(config_get("path"), self.title))

	def directDownload(self):
		n = self.videosBox.Selection
		url = self.result.get_url(n)
		title = self.result.get_title(n)
		logger.info("Direct download from playlist. title=%s url=%s", title, url)
		dlg = DownloadProgress(wx.GetApp().GetTopWindow(), title)
		direct_download(int(config_get('defaultformat')), url, dlg, "video", os.path.join(config_get("path"), self.title))


	def onM4aDownload(self, event):
		n = self.videosBox.Selection
		url = self.result.get_url(n)
		title = self.result.get_title(n)
		logger.info("Downloading playlist video as m4a. title=%s url=%s", title, url)
		dlg = DownloadProgress(wx.GetApp().GetTopWindow(), title)
		direct_download(1, url, dlg, "video", os.path.join(config_get("path"), self.title))

	def onMp3Download(self, event):
		n = self.videosBox.Selection
		url = self.result.get_url(n)
		title = self.result.get_title(n)
		logger.info("Downloading playlist video as mp3. title=%s url=%s", title, url)
		dlg = DownloadProgress(wx.GetApp().GetTopWindow(), title)
		direct_download(2, url, dlg, "video", os.path.join(config_get("path"), self.title))

	def onDownload(self, event):
		downloadMenu = wx.Menu()
		videoItem = downloadMenu.Append(-1, _("Video"))
		audioMenu = wx.Menu()
		m4aItem = audioMenu.Append(-1, "m4a")
		mp3Item = audioMenu.Append(-1, "mp3")
		downloadMenu.Append(-1, _("audio"), audioMenu)
		self.Bind(wx.EVT_MENU, self.onVideoDownload, videoItem)
		self.Bind(wx.EVT_MENU, self.onM4aDownload, m4aItem)
		self.Bind(wx.EVT_MENU, self.onMp3Download, mp3Item)
		self.PopupMenu(downloadMenu)
		self.videosBox.SetFocus()
	def back(self):
		self.Parent.Show()
		self.Destroy()

	def onHook(self, event):
		if not self.IsShown():
			event.Skip()
			return
		if event.KeyCode == wx.WXK_ESCAPE:
			if get_active_media_window() is not None:
				event.Skip()
				return
			self.back()
		else:
			event.Skip()
