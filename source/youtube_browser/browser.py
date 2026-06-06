
import webbrowser
from threading import Thread


import pyperclip
import wx
from gui.download_progress import DownloadProgress
from gui.search_dialog import SearchDialog
from gui.settings_dialog import SettingsDialog
from gui.playlist_dialog import PlaylistDialog
from gui.activity_dialog import LoadingDialog

from download_handler.downloader import downloadAction
from media_player.media_gui import MediaGui
from media_player.player import Player
from nvda_client.client import speak
from settings_handler import config_get
from youtube_browser.search_handler import Search
from utiles import direct_download, get_audio_stream, get_video_stream
from database import Favorite, Continue
from app_logger import get_logger


logger = get_logger()


class YoutubeBrowser(wx.Frame):
	def __init__(self, parent):
		wx.Frame.__init__(self, parent=parent, title=parent.Title)
		self.Centre()
		self.SetSize(wx.DisplaySize())
		self.Maximize(True)
		self.panel = wx.Panel(self)
		lbl = wx.StaticText(self.panel, -1, _("search results: "))
		self.searchResults = wx.ListBox(self.panel, -1)
		self.loadMoreButton = wx.Button(self.panel, -1, _("load more results"))
		self.loadMoreButton.Enabled = False
		self.loadMoreButton.Show(not config_get("autoload"))
		self.playButton = wx.Button(self.panel, -1, _("play (enter)"), name="controls")
		self.downloadButton = wx.Button(self.panel, -1, _("download"), name="controls")
		self.favCheck = wx.CheckBox(self.panel, -1, _("favorite the video"))
		searchButton = wx.Button(self.panel, -1, _("search... (ctrl+f)"))
		backButton = wx.Button(self.panel, -1, _("return to the main window"))
		sizer = wx.BoxSizer(wx.VERTICAL)
		sizer1 = wx.BoxSizer(wx.HORIZONTAL)
		sizer1.Add(backButton, 1, wx.ALL)
		sizer1.Add(searchButton, 1, wx.ALL)
		sizer2 = wx.BoxSizer(wx.HORIZONTAL)
		for control in self.panel.GetChildren():
			if control.Name == "controls":
				sizer2.Add(control, 1)
		sizer.Add(sizer1, 1, wx.EXPAND)
		sizer.Add(lbl, 1, wx.ALL)
		sizer.Add(self.searchResults, 1, wx.EXPAND)
		sizer.Add(self.loadMoreButton, 1)
		sizer.Add(sizer2, 1)
		self.panel.SetSizer(sizer)
		self.contextSetup()
		results_shortcuts = wx.AcceleratorTable([
			(0, wx.WXK_RETURN, self.audioPlayItemId),
			(wx.ACCEL_CTRL, wx.WXK_RETURN, self.videoPlayItemId)
		])
		self.searchResults.SetAcceleratorTable(results_shortcuts)
		menuBar = wx.MenuBar()
		optionsMenu = wx.Menu()
		settingsItem = optionsMenu.Append(-1, _("settings...\talt+s"))
		hotKeys = wx.AcceleratorTable([
			(wx.ACCEL_ALT, ord("S"), settingsItem.GetId()),
			(wx.ACCEL_CTRL, ord("F"), searchButton.GetId()),
			(wx.ACCEL_CTRL, ord("D"), self.directDownloadId),
			(wx.ACCEL_CTRL, ord("L"), self.copyItemId)
		])
		# hotkey table
		self.SetAcceleratorTable(hotKeys)
		menuBar.Append(optionsMenu, _("options"))
		self.SetMenuBar(menuBar)
		self.Bind(wx.EVT_MENU, lambda event: SettingsDialog(self), settingsItem)
		self.loadMoreButton.Bind(wx.EVT_BUTTON, self.onLoadMore)
		self.playButton.Bind(wx.EVT_BUTTON, lambda event: self.playVideo())
		self.downloadButton.Bind(wx.EVT_BUTTON, self.onDownload)
		self.favCheck.Bind(wx.EVT_CHECKBOX, self.onFavorite)
		searchButton.Bind(wx.EVT_BUTTON, self.onSearch)
		backButton.Bind(wx.EVT_BUTTON, lambda event: self.backAction())
		self.Bind(wx.EVT_CHAR_HOOK, self.onHook)

		self.Bind(wx.EVT_LISTBOX_DCLICK, lambda event: self.playVideo(), self.searchResults)
		self.searchResults.Bind(wx.EVT_LISTBOX, self.onListBox)
		self.Bind(wx.EVT_SHOW, self.onShow)
		self.Bind(wx.EVT_CLOSE, lambda event: wx.Exit())
		if self.searchAction():
			self.Show()
			self.Parent.Hide()
		else:
			self.Destroy()
		self.favorites = Favorite()
		self.togleFavorite()

	def searchAction(self, value=""):
		dialog = SearchDialog(self, value=value)
		query = dialog.query
		filter = dialog.filter
		if query is None:
			self.togleControls()
			return
		try:
			logger.info("Searching YouTube. query=%s filter=%s", query, filter)
			self.search = LoadingDialog(self, _("searching"), Search, query, filter).res
		except Exception:
			logger.exception("YouTube search failed. query=%s filter=%s", query, filter)
			wx.MessageBox(_("unable to get search results due to a network connection."), _("error"), style=wx.ICON_ERROR)
			self.searchAction(query)
		titles = self.search.get_titles()
		self.searchResults.Set(titles)
		self.togleControls()
		try:
			self.searchResults.SetSelection(0)
		except:
			pass
		self.searchResults.SetFocus()
		self.togleDownload()
		self.toglePlay()
		return True

	def onSearch(self, event):
		if hasattr(self, "search"):
			self.searchAction(self.search.query)
		else:
			self.searchAction()

	def playVideo(self):
		number = self.searchResults.Selection
		if self.search.get_type(number) == "playlist":

			PlaylistDialog(self, self.search.get_url(number))
			return
		title = self.search.get_title(number)
		url = self.search.get_url(number)
		logger.info("Playing video from search results. title=%s url=%s", title, url)
		stream = LoadingDialog(self, _("playing"), get_video_stream, url).res
		gui = MediaGui(self, title, stream, url, True if self.search.get_views(number) is not None else False, results=self.search, history_data=self.search.get_history_data(number))
		self.Hide()

	def playAudio(self):
		number = self.searchResults.Selection
		if self.search.get_type(number) == "playlist":
			return
		title = self.search.get_title(number)
		url = self.search.get_url(number)
		logger.info("Playing audio from search results. title=%s url=%s", title, url)
		stream = LoadingDialog(self, _("playing"), get_audio_stream, url).res
		gui = MediaGui(self, title, stream, url, results=self.search, audio_mode=True, history_data=self.search.get_history_data(number))
		self.Hide()


	def onHook(self, event):

		if event.KeyCode == wx.WXK_SPACE and self.search.get_type(self.searchResults.Selection) == "video" and self.FindFocus() == self.searchResults:
			self.favCheck.Value = not self.favCheck.Value
			self.onFavorite(None)
		elif event.KeyCode == wx.WXK_BACK and not type(self.FindFocus()) == MediaGui:
			self.backAction()
		else:
			event.Skip()
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
		openChannelItem = self.contextMenu.Append(-1, _("navigate to the channel"))
		downloadChannelItem = self.contextMenu.Append(-1, _("download channel"))
		copyItem = self.contextMenu.Append(-1, _("copy video link"))
		self.copyItemId = copyItem.GetId()
		webbrowserItem = self.contextMenu.Append(-1, _("open in browser"))
		def popup():
			if self.searchResults.Strings != []:
				self.searchResults.PopupMenu(self.contextMenu)
		self.searchResults.Bind(wx.EVT_MENU, lambda event: self.playVideo(), id=self.videoPlayItemId)
		self.searchResults.Bind(wx.EVT_MENU, lambda event: self.playAudio(), id=self.audioPlayItemId)
		self.searchResults.Bind(wx.EVT_MENU, self.onOpenChannel, openChannelItem)
		self.searchResults.Bind(wx.EVT_MENU, self.onDownloadChannel, downloadChannelItem)
		self.Bind(wx.EVT_MENU, self.onCopy, copyItem)
		self.Bind(wx.EVT_MENU, self.onOpenInBrowser, webbrowserItem)
		self.searchResults.Bind(wx.EVT_CONTEXT_MENU, lambda event: popup())
		self.Bind(wx.EVT_MENU, self.onVideoDownload, videoItem)
		self.Bind(wx.EVT_MENU, self.onM4aDownload, m4aItem)
		self.Bind(wx.EVT_MENU, self.onMp3Download, mp3Item)
		self.Bind(wx.EVT_MENU, lambda event: self.directDownload(), directDownloadItem)

	def onOpenChannel(self, event):
		n = self.searchResults.Selection
		webbrowser.open(self.search.get_channel(n)["url"])
	def onDownloadChannel(self, event):
		n = self.searchResults.Selection
		channel = self.search.get_channel(n)
		title = channel["name"]
		url = channel["url"]
		download_type = "channel"
		logger.info("Downloading channel. title=%s url=%s", title, url)
		dlg = DownloadProgress(wx.GetApp().GetTopWindow(), title)
		direct_download(int(config_get('defaultformat')), url, dlg, download_type)

	def onOpenInBrowser(self, event):
		number = self.searchResults.Selection
		url = self.search.get_url(number)
		webbrowser.open(url)
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

	def onM4aDownload(self, event):
		url = self.search.get_url(self.searchResults.Selection)
		title = self.search.get_title(self.searchResults.Selection)
		download_type = self.search.get_type(self.searchResults.Selection)
		logger.info("Downloading search result as m4a. title=%s type=%s url=%s", title, download_type, url)
		dlg = DownloadProgress(wx.GetApp().GetTopWindow(), title)
		direct_download(1, url, dlg, download_type)

	def onMp3Download(self, event):
		url = self.search.get_url(self.searchResults.Selection)
		title = self.search.get_title(self.searchResults.Selection)
		download_type = self.search.get_type(self.searchResults.Selection)
		logger.info("Downloading search result as mp3. title=%s type=%s url=%s", title, download_type, url)
		dlg = DownloadProgress(wx.GetApp().GetTopWindow(), title)
		direct_download(2, url, dlg, download_type)

	def onVideoDownload(self, event):
		url = self.search.get_url(self.searchResults.Selection)
		title = self.search.get_title(self.searchResults.Selection)
		download_type = self.search.get_type(self.searchResults.Selection)
		logger.info("Downloading search result as video. title=%s type=%s url=%s", title, download_type, url)
		dlg = DownloadProgress(wx.GetApp().GetTopWindow(), title)
		direct_download(0, url, dlg, download_type)



	def onCopy(self, event):
		pyperclip.copy(self.search.get_url(self.searchResults.Selection))
		wx.MessageBox(_("video URL has been copyed successfully."), _("done"), parent=self)
	def loadMore(self):
		if self.searchResults.Strings == []:
			return
		speak(_("loading more results..."))
		if self.search.load_more() is None:
			logger.warning("Could not load more search results")
			speak(_("unable to load more results"))
			return
		# position = self.searchResults.Selection
		wx.CallAfter(self.searchResults.Append, self.search.get_last_titles())
		speak(_("more results loaded successfully"))
		wx.CallAfter(self.searchResults.SetFocus)
	def onListBox(self, event):
		self.togleDownload()
		self.toglePlay()
		self.togleFavorite()
		if self.searchResults.Selection == len(self.searchResults.Strings)-1:
			if not config_get("autoload"):
				self.loadMoreButton.Enabled = True
				return
			Thread(target=self.loadMore).start()
		else:
			self.loadMoreButton.Enabled = False
	def onLoadMore(self, event):
		Thread(target=self.loadMore).start()
	def backAction(self):
		self.Destroy()
		self.Parent.Show()
	def togleControls(self):
		if self.searchResults.Strings == []:
			for control in self.panel.GetChildren():
				if control.Name == "controls":
					control.Hide()
			self.loadMoreButton.Hide()
		else:
			for control in self.panel.GetChildren():
				if control.Name == "controls":
					control.Show()
			self.loadMoreButton.Show(not config_get("autoload"))
	def togleDownload(self):
		n = self.searchResults.Selection
		if self.search.get_views(n) is None and self.search.get_type(n) == "video":
			self.contextMenu.Enable(self.downloadId, False)
			self.contextMenu.Enable(self.directDownloadId, False)
			self.downloadButton.Enabled = False
			return
		self.contextMenu.Enable(self.downloadId, True)
		self.contextMenu.Enable(self.directDownloadId, True)
		self.downloadButton.Enabled = True

	def toglePlay(self):
		n = self.searchResults.Selection
		contextMenuIds = (self.videoPlayItemId, self.audioPlayItemId)
		if self.search.get_type(n) == "playlist":
			self.playButton.Label = _("open")
			for i in contextMenuIds:
				self.contextMenu.Enable(i, False)
			return
			self.playButton.Enabled = True
			for i in contextMenuIds:
				self.contextMenu.Enable(i, True)
	def onFavorite(self, event):
		n = self.searchResults.Selection
		url = self.search.get_url(n)
		if self.favCheck.Value:
			title = self.search.get_title(n)
			display_title = f"{title}. {self.search.get_channel(n)['name']}"
			channel_url = self.search.get_channel(n)['url']
			channel_name = self.search.get_channel(n)['name']
			live = 1 if not self.search.get_views(n) else 0
			data = {"title": title, "display_title": display_title, "url": url, "live": live, "channel_url": channel_url, "channel_name": channel_name}
			logger.info("Adding favorite. title=%s url=%s", title, url)
			self.favorites.add_favorite(data)
			speak(_("added to the favorites list successfully"))
		else:
			logger.info("Removing favorite. url=%s", url)
			self.favorites.remove_favorite(url)
			speak(_("deleted from favorite list"))

	def togleFavorite(self):
		n = self.searchResults.Selection
		self.favCheck.Enabled = self.search.get_type(n) == "video"
		if not self.favCheck.Enabled:
			return
		rows = self.favorites.get_all()
		url = self.search.get_url(n)
		def check_url(url):
			for row in rows:
				if url == row["url"]:
					wx.CallAfter(self.favCheck.SetValue, True)
					break
			else:
					wx.CallAfter(self.favCheck.SetValue, False)
		Thread(target=check_url, args=[url]).start()

	def directDownload(self):
		n = self.searchResults.Selection
		if self.search.get_views(n) is None and self.search.get_type(n) == "video":
			return
		url = self.search.get_url(self.searchResults.Selection)
		title = self.search.get_title(self.searchResults.Selection)
		download_type = self.search.get_type(self.searchResults.Selection)
		logger.info("Direct download from search result. title=%s type=%s url=%s", title, download_type, url)
		dlg = DownloadProgress(wx.GetApp().GetTopWindow(), title)
		direct_download(int(config_get('defaultformat')), url, dlg, download_type)
	def onShow(self, event):
		self.searchResults.SetFocus()
