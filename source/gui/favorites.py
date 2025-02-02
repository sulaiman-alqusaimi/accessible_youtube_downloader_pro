import wx
import application
from database import Favorite
from utiles import direct_download, get_audio_stream, get_video_stream
from media_player.media_gui import MediaGui
from nvda_client.client import speak
import pyperclip
from gui.download_progress import DownloadProgress
from .activity_dialog import LoadingDialog
from settings_handler import config_get
import webbrowser


class Favorites(wx.Frame):
	def __init__(self, parent):
		super().__init__(parent, title=application.name)
		self.Centre()
		self.SetSize(wx.DisplaySize())
		self.Maximize(True)
		p = wx.Panel(self)
		l1 = wx.StaticText(p, -1, _("المفضلة: "))
		self.favList = wx.ListBox(p, -1)
		self.playButton = wx.Button(p, -1, _("تشغيل"), name="control")
		self.downloadButton = wx.Button(p, -1, _("تنزيل"), name="control")
		self.deleteButton = wx.Button(p, -1, _("إلغاء التفضيل"), name="control")
		backButton = wx.Button(p, -1, _("العودة إلى النافذة الرئيسية"), name="control")
		self.favorites = Favorite()
		self.rows = self.favorites.get_all()
		self.favList.Set([row["display_title"] for row in self.rows])
		if self.favList.Strings:
			self.favList.Selection = 0
			self.contextSetup()
			hotkeys = wx.AcceleratorTable([
				(0, wx.WXK_RETURN, self.audioPlayItemId),
				(wx.ACCEL_CTRL, wx.WXK_RETURN, self.videoPlayItemId),
				(wx.ACCEL_CTRL, ord("D"), self.directDownloadId),
			(wx.ACCEL_CTRL, ord("L"), self.copyItemId),
			])
			self.favList.SetAcceleratorTable(hotkeys)
		sizer = wx.BoxSizer(wx.VERTICAL)
		sizer.Add(l1, 1)
		sizer.Add(self.favList, 1, wx.EXPAND)
		ctrlSizer = wx.BoxSizer(wx.HORIZONTAL)
		for control in p.GetChildren():
			if control.Name == "control":
				ctrlSizer.Add(control, 1)
		sizer.Add(ctrlSizer)
		self.togleControls()

		self.playButton.Bind(wx.EVT_BUTTON, lambda e: self.playVideo())
		self.downloadButton.Bind(wx.EVT_BUTTON, self.onDownload)
		self.deleteButton.Bind(wx.EVT_BUTTON, self.onDelete)
		backButton.Bind(wx.EVT_BUTTON, self.onBack)
		self.Bind(wx.EVT_CLOSE, lambda e: wx.Exit())
		self.Bind(wx.EVT_CHAR_HOOK, self.onHook)
		p.SetSizer(sizer)
		sizer.Fit(p)
		self.Show()
	def onDelete(self, event):
		n = self.favList.Selection
		if n == -1:
			return
		url = self.rows[n]["url"]
		self.favorites.remove_favorite(url)
		self.favList.Delete(n)
		self.rows.pop(n)
		self.togleControls()
		try:
			self.favList.Selection = n
		except:
			pass
		self.favList.SetFocus()
		speak(_("تم حذف الفيديو من قائمة المفضلة"))
	def playVideo(self):
		n = self.favList.Selection
		url = self.rows[n]["url"]
		title = self.rows[n]["title"]
		stream = LoadingDialog(self, _("جاري التشغيل"), get_video_stream, url).res
		gui = MediaGui(self, title, stream, url, True if not self.rows[n]["live"] else False, self.rows)
		self.Hide()

	def playAudio(self):
		n = self.favList.Selection
		url = self.rows[n]["url"]
		title = self.rows[n]["title"]
		stream = LoadingDialog(self, _("جاري التشغيل"), get_audio_stream, url).res
		gui = MediaGui(self, title, stream, url, audio_mode=True, results=self.rows)
		self.Hide()

	def togleControls(self):
		for control in (self.playButton, self.downloadButton, self.deleteButton):
			if self.rows == []:
				control.Disable()

	def contextSetup(self):
		self.contextMenu = wx.Menu()
		videoPlayItem = self.contextMenu.Append(-1, _("تشغيل"))
		self.videoPlayItemId = videoPlayItem.GetId()
		audioPlayItem = self.contextMenu.Append(-1, _("التشغيل كمقطع صوتي"))
		self.audioPlayItemId = audioPlayItem.GetId()
		self.downloadMenu = wx.Menu()
		videoItem = self.downloadMenu.Append(-1, _("فيديو"))
		audioMenu = wx.Menu()
		m4aItem = audioMenu.Append(-1, "m4a")
		mp3Item = audioMenu.Append(-1, "mp3")
		self.downloadMenu.AppendSubMenu(audioMenu, _("صوت"))
		self.downloadId = self.contextMenu.AppendSubMenu(self.downloadMenu, _("تنزيل")).GetId()
		directDownloadItem = self.contextMenu.Append(-1, _("التنزيل المباشر...\tctrl+d"))
		self.directDownloadId = directDownloadItem.GetId()
		openChannelItem = self.contextMenu.Append(-1, _("الانتقال إلى القناة"))
		downloadChannelItem = self.contextMenu.Append(-1, _("تنزيل القناة"))
		copyItem = self.contextMenu.Append(-1, _("نسخ رابط المقطع"))
		self.copyItemId = copyItem.GetId()
		webbrowserItem = self.contextMenu.Append(-1, _("الفتح من خلال متصفح الإنترنت"))
		def popup():
			if self.rows != []:
				self.favList.PopupMenu(self.contextMenu)
		self.favList.Bind(wx.EVT_CONTEXT_MENU, lambda event: popup())
		self.favList.Bind(wx.EVT_MENU, lambda e: self.playVideo(), id=self.videoPlayItemId)
		self.favList.Bind(wx.EVT_MENU, lambda e: self.playAudio(), id=self.audioPlayItemId)
		self.favList.Bind(wx.EVT_MENU, self.onCopy, id=self.copyItemId)
		self.favList.Bind(wx.EVT_MENU, lambda e: self.directDownload(), id=self.directDownloadId)
		self.Bind(wx.EVT_MENU, self.onVideoDownload, videoItem)

		self.Bind(wx.EVT_MENU, self.onM4aDownload, m4aItem)
		self.Bind(wx.EVT_MENU, self.onMp3Download, mp3Item)
		self.favList.Bind(wx.EVT_MENU, self.onOpenChannel, openChannelItem)
		self.favList.Bind(wx.EVT_MENU, self.onDownloadChannel, downloadChannelItem)
		self.Bind(wx.EVT_MENU, self.onOpenInBrowser, webbrowserItem)
	def onOpenInBrowser(self, event):
		n = self.favList.Selection
		webbrowser.open(self.rows[n]["url"])


	def onOpenChannel(self, event):
		n = self.favList.Selection
		webbrowser.open(self.rows[n]["channel_url"])


	def onDownloadChannel(self, event):
		n = self.favList.Selection
		title = self.rows[n]["channel_name"]
		url = self.rows[n]["channel_url"]
		download_type = "channel"
		dlg = DownloadProgress(wx.GetApp().GetTopWindow(), title)
		direct_download(int(config_get('defaultformat')), url, dlg, download_type)



	def onCopy(self, event):
		pyperclip.copy(self.rows[self.favList.Selection]["url"])
		wx.MessageBox(_("تم نسخ رابط المقطع بنجاح"), _("اكتمال"), parent=self)

	def directDownload(self):
		n = self.favList.Selection

		url = self.rows[n]["url"]
		title = self.rows[n]["title"]
		dlg = DownloadProgress(wx.GetApp().GetTopWindow(), title)
		direct_download(int(config_get('defaultformat')), url, dlg, "video")

	def onM4aDownload(self, event):
		n = self.favList.Selection
		url = self.rows[n]["url"]
		title = self.rows[n]["title"]

		dlg = DownloadProgress(wx.GetApp().GetTopWindow(), title)
		direct_download(1, url, dlg, "video")


	def onMp3Download(self, event):
		n = self.favList.Selection
		url = self.rows[n]["url"]
		title = self.rows[n]["title"]
		dlg = DownloadProgress(wx.GetApp().GetTopWindow(), title)
		direct_download(2, url, dlg, "video")

	def onVideoDownload(self, event):
		n = self.favList.Selection
		url = self.rows[n]["url"]
		title = self.rows[n]["title"]
		dlg = DownloadProgress(wx.GetApp().GetTopWindow(), title)
		direct_download(0, url, dlg, "video")


	def onDownload(self, event):
		downloadMenu = wx.Menu()
		videoItem = downloadMenu.Append(-1, _("فيديو"))
		audioMenu = wx.Menu()
		m4aItem = audioMenu.Append(-1, "m4a")
		mp3Item = audioMenu.Append(-1, "mp3")
		downloadMenu.Append(-1, _("صوت"), audioMenu)
		self.Bind(wx.EVT_MENU, self.onVideoDownload, videoItem)
		self.Bind(wx.EVT_MENU, self.onM4aDownload, m4aItem)
		self.Bind(wx.EVT_MENU, self.onMp3Download, mp3Item)
		self.PopupMenu(downloadMenu)
	def onHook(self, event):
		event.Skip()
		if event.KeyCode in (wx.WXK_DELETE, wx.WXK_NUMPAD_DELETE) and self.FindFocus() == self.favList:
			self.onDelete(None)
		elif event.KeyCode == wx.WXK_BACK:
			self.onBack(None)

	def onBack(self, event):
		self.Parent.Show()
		self.Destroy()