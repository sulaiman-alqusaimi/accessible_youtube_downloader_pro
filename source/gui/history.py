import webbrowser

import application
import pyperclip
import wx
from database import ViewHistory
from gui.download_progress import DownloadProgress
from media_player.media_gui import MediaGui
from nvda_client.client import speak
from settings_handler import config_get
from utiles import direct_download, get_audio_stream, get_video_stream
from .activity_dialog import LoadingDialog
from app_logger import get_logger


logger = get_logger()


class History(wx.Frame):
	def __init__(self, parent):
		logger.info("Opening view history window")
		super().__init__(parent, title=application.name)
		self.Centre()
		self.SetSize(wx.DisplaySize())
		self.Maximize(True)
		p = wx.Panel(self)
		l1 = wx.StaticText(p, -1, _("view history"))
		self.historyList = wx.ListBox(p, -1)
		self.playButton = wx.Button(p, -1, _("play"), name="control")
		self.downloadButton = wx.Button(p, -1, _("download"), name="control")
		self.deleteButton = wx.Button(p, -1, _("delete from history"), name="control")
		self.clearButton = wx.Button(p, -1, _("clear history"), name="control")
		backButton = wx.Button(p, -1, _("return to the main window"), name="control")
		self.history = ViewHistory()
		self.rows = self.history.get_all() or []
		self.historyList.Set([row["display_title"] for row in self.rows])
		if self.historyList.Strings:
			self.historyList.Selection = 0
		self.contextSetup()
		hotkeys = wx.AcceleratorTable([
			(0, wx.WXK_RETURN, self.audioPlayItemId),
			(wx.ACCEL_CTRL, wx.WXK_RETURN, self.videoPlayItemId),
			(wx.ACCEL_CTRL, ord("D"), self.directDownloadId),
			(wx.ACCEL_CTRL, ord("L"), self.copyItemId),
		])
		self.historyList.SetAcceleratorTable(hotkeys)
		sizer = wx.BoxSizer(wx.VERTICAL)
		sizer.Add(l1, 1)
		sizer.Add(self.historyList, 1, wx.EXPAND)
		ctrlSizer = wx.BoxSizer(wx.HORIZONTAL)
		for control in p.GetChildren():
			if control.Name == "control":
				ctrlSizer.Add(control, 1)
		sizer.Add(ctrlSizer)
		self.togleControls()
		self.playButton.Bind(wx.EVT_BUTTON, lambda e: self.playVideo())
		self.downloadButton.Bind(wx.EVT_BUTTON, self.onDownload)
		self.deleteButton.Bind(wx.EVT_BUTTON, self.onDelete)
		self.clearButton.Bind(wx.EVT_BUTTON, self.onClear)
		backButton.Bind(wx.EVT_BUTTON, self.onBack)
		self.Bind(wx.EVT_CLOSE, lambda e: wx.Exit())
		self.Bind(wx.EVT_CHAR_HOOK, self.onHook)
		p.SetSizer(sizer)
		sizer.Fit(p)
		self.Show()

	def selected_row(self):
		n = self.historyList.Selection
		if n == -1 or n >= len(self.rows):
			return None
		return self.rows[n]

	def onDelete(self, event):
		n = self.historyList.Selection
		row = self.selected_row()
		if row is None:
			return
		logger.info("Deleting view history item. id=%s url=%s", row["id"], row["url"])
		self.history.remove(row["id"])
		self.historyList.Delete(n)
		self.rows.pop(n)
		self.togleControls()
		if self.rows:
			self.historyList.Selection = min(n, len(self.rows)-1)
		self.historyList.SetFocus()
		speak(_("deleted from history"))

	def onClear(self, event):
		if not self.rows:
			return
		logger.info("Clearing view history")
		self.history.clear()
		self.rows = []
		self.historyList.Clear()
		self.togleControls()
		self.historyList.SetFocus()
		speak(_("history cleared"))

	def playVideo(self):
		row = self.selected_row()
		if row is None:
			return
		logger.info("Playing history video. title=%s url=%s", row["title"], row["url"])
		stream = LoadingDialog(self, _("playing"), get_video_stream, row["url"]).res
		gui = MediaGui(self, row["title"], stream, row["url"], True, self.rows, history_data=row)
		self.Hide()

	def playAudio(self):
		row = self.selected_row()
		if row is None:
			return
		logger.info("Playing history audio. title=%s url=%s", row["title"], row["url"])
		stream = LoadingDialog(self, _("playing"), get_audio_stream, row["url"]).res
		gui = MediaGui(self, row["title"], stream, row["url"], audio_mode=True, results=self.rows, history_data=row)
		self.Hide()

	def togleControls(self):
		for control in (self.playButton, self.downloadButton, self.deleteButton, self.clearButton):
			control.Enable(bool(self.rows))

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
		copyItem = self.contextMenu.Append(-1, _("copy video link"))
		self.copyItemId = copyItem.GetId()
		webbrowserItem = self.contextMenu.Append(-1, _("open in browser"))
		deleteItem = self.contextMenu.Append(-1, _("delete from history"))
		def popup():
			if self.rows != []:
				self.historyList.PopupMenu(self.contextMenu)
		self.historyList.Bind(wx.EVT_CONTEXT_MENU, lambda event: popup())
		self.historyList.Bind(wx.EVT_MENU, lambda e: self.playVideo(), id=self.videoPlayItemId)
		self.historyList.Bind(wx.EVT_MENU, lambda e: self.playAudio(), id=self.audioPlayItemId)
		self.historyList.Bind(wx.EVT_MENU, self.onCopy, id=self.copyItemId)
		self.historyList.Bind(wx.EVT_MENU, lambda e: self.directDownload(), id=self.directDownloadId)
		self.Bind(wx.EVT_MENU, self.onVideoDownload, videoItem)
		self.Bind(wx.EVT_MENU, self.onM4aDownload, m4aItem)
		self.Bind(wx.EVT_MENU, self.onMp3Download, mp3Item)
		self.Bind(wx.EVT_MENU, self.onOpenInBrowser, webbrowserItem)
		self.historyList.Bind(wx.EVT_MENU, self.onDelete, deleteItem)

	def onOpenInBrowser(self, event):
		row = self.selected_row()
		if row is not None:
			webbrowser.open(row["url"])

	def onCopy(self, event):
		row = self.selected_row()
		if row is None:
			return
		pyperclip.copy(row["url"])
		wx.MessageBox(_("video URL has been copyed successfully."), _("done"), parent=self)

	def directDownload(self):
		row = self.selected_row()
		if row is None:
			return
		logger.info("Direct download from history. title=%s url=%s", row["title"], row["url"])
		dlg = DownloadProgress(wx.GetApp().GetTopWindow(), row["title"])
		direct_download(int(config_get('defaultformat')), row["url"], dlg, "video")

	def onM4aDownload(self, event):
		row = self.selected_row()
		if row is None:
			return
		logger.info("Downloading history item as m4a. title=%s url=%s", row["title"], row["url"])
		dlg = DownloadProgress(wx.GetApp().GetTopWindow(), row["title"])
		direct_download(1, row["url"], dlg, "video")

	def onMp3Download(self, event):
		row = self.selected_row()
		if row is None:
			return
		logger.info("Downloading history item as mp3. title=%s url=%s", row["title"], row["url"])
		dlg = DownloadProgress(wx.GetApp().GetTopWindow(), row["title"])
		direct_download(2, row["url"], dlg, "video")

	def onVideoDownload(self, event):
		row = self.selected_row()
		if row is None:
			return
		logger.info("Downloading history item as video. title=%s url=%s", row["title"], row["url"])
		dlg = DownloadProgress(wx.GetApp().GetTopWindow(), row["title"])
		direct_download(0, row["url"], dlg, "video")

	def onDownload(self, event):
		downloadMenu = wx.Menu()
		videoItem = downloadMenu.Append(-1, _("Video"))
		audioMenu = wx.Menu()
		m4aItem = audioMenu.Append(-1, "m4a")
		mp3Item = audioMenu.Append(-1, "mp3")
		downloadMenu.AppendSubMenu(audioMenu, _("audio"))
		self.Bind(wx.EVT_MENU, self.onVideoDownload, videoItem)
		self.Bind(wx.EVT_MENU, self.onM4aDownload, m4aItem)
		self.Bind(wx.EVT_MENU, self.onMp3Download, mp3Item)
		self.PopupMenu(downloadMenu)

	def onHook(self, event):
		if event.KeyCode in (wx.WXK_DELETE, wx.WXK_NUMPAD_DELETE) and self.FindFocus() == self.historyList:
			self.onDelete(None)
		elif event.KeyCode == wx.WXK_BACK:
			self.onBack(None)
		else:
			event.Skip()

	def onBack(self, event):
		self.Parent.Show()
		self.Destroy()
