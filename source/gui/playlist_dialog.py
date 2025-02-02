import wx
from youtube_browser.search_handler import PlaylistResult
from utiles import direct_download, get_audio_stream, get_video_stream
from media_player.media_gui import MediaGui
from nvda_client.client import speak
import pyperclip
from gui.download_progress import DownloadProgress
from settings_handler import config_get
import webbrowser
from threading import Thread
import os
from .activity_dialog import LoadingDialog
import application

class PlaylistDialog(wx.Dialog):
	def __init__(self, parent, url):
		super().__init__(parent, title=application.name)
		self.CenterOnParent()
		self.url = url
		self.Maximize(True)
		p = wx.Panel(self)
		l1 = wx.StaticText(p, -1, _("قائمة الفيديوهات: "))
		self.videosBox = wx.ListBox(p, -1)
		self.playButton = wx.Button(p, -1, _("تشغيل"), name="control")
		self.downloadButton = wx.Button(p, -1, _("تنزيل"), name="control")
		backButton = wx.Button(p, -1, _("رجوع"), name="control")
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
			self.result = LoadingDialog(self.Parent, _("جاري عرض قائمة التشغيل"), PlaylistResult, self.url).res
			self.title = self.result.playlist.info['info']['title']
			self.SetTitle(f"{application.name} - {self.title}")
			self.videosBox.Set(self.result.get_display_titles())
		except:
			wx.MessageBox(_("حدث خطأ ما أثناء محاولة فتح قائمة التشغيل"), _("خطأ"), style=wx.ICON_ERROR, parent=self)
			self.Destroy()
			return
		self.Parent.Hide()
		self.Show()
		self.videosBox.Selection = 0
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
		self.videosBox.Bind(wx.EVT_MENU, self.onOpenChannel, openChannelItem)
		self.videosBox.Bind(wx.EVT_MENU, self.onDownloadChannel, downloadChannelItem)
		self.Bind(wx.EVT_MENU, self.onOpenInBrowser, webbrowserItem)

	def onOpenInBrowser(self, event):
		n = self.videosBox.Selection
		webbrowser.open(self.result.get_url(n))

	def onCopy(self, event):
		n = self.videosBox.Selection
		pyperclip.copy(self.result.get_url(n))
		wx.MessageBox(_("تم نسخ رابط المقطع بنجاح"), _("اكتمال"), parent=self)

	def onOpenChannel(self, event):
		n = self.videosBox.Selection
		webbrowser.open(self.result.videos[n]['channel']['url'])

	def onDownloadChannel(self, event):
		n = self.videosBox.Selection
		title = self.result.videos[n]["channel"]['name']
		url = self.result.videos[n]["channel"]['url']
		download_type = "channel"
		dlg = DownloadProgress(wx.GetApp().GetTopWindow(), title)
		direct_download(int(config_get('defaultformat')), url, dlg, download_type)

	def playVideo(self):
		n = self.videosBox.Selection
		url = self.result.get_url(n)

		title = self.result.get_title(n)

		stream = LoadingDialog(self, _("جاري التشغيل"), get_video_stream, url).res
		gui = MediaGui(self, title, stream, url, True, self.result)
		gui.path = os.path.join(gui.path, self.title)
		self.Hide()

	def playAudio(self):
		n = self.videosBox.Selection
		url = self.result.get_url(n)

		title = self.result.get_title(n)

		stream = LoadingDialog(self, _("جاري التشغيل"), get_audio_stream, url).res

		gui = MediaGui(self, title, stream, url, audio_mode=True, results=self.result)
		gui.path = os.path.join(gui.path, self.title)
		self.Hide()


	def onListBox(self, event):
		n = self.videosBox.Selection
		if n == self.videosBox.Count-1:
			def load():
				try:
					if self.result.next():
						titles = self.result.get_new_titles()
						wx.CallAfter(self.videosBox.Append, titles)
						speak(_("تم تحميل المزيد من الفيديوهات"))
					else:
						speak(_("ليس هناك فيديوهات أخرى"))
				except Exception as e:
					speak(_("لم يتم تحميل المزيد من الفيديوهات"))
			Thread(target=load).start()
	def onVideoDownload(self, event):
		n = self.videosBox.Selection
		url = self.result.get_url(n)
		title = self.result.get_title(n)
		dlg = DownloadProgress(self.Parent, title)
		direct_download(0, url, dlg, "video", os.path.join(config_get("path"), self.title))

	def directDownload(self):
		n = self.videosBox.Selection
		url = self.result.get_url(n)
		title = self.result.get_title(n)
		dlg = DownloadProgress(wx.GetApp().GetTopWindow(), title)
		direct_download(int(config_get('defaultformat')), url, dlg, "video", os.path.join(config_get("path"), self.title))


	def onM4aDownload(self, event):
		n = self.videosBox.Selection
		url = self.result.get_url(n)
		title = self.result.get_title(n)
		dlg = DownloadProgress(wx.GetApp().GetTopWindow(), title)
		direct_download(1, url, dlg, "video", os.path.join(config_get("path"), self.title))

	def onMp3Download(self, event):
		n = self.videosBox.Selection
		url = self.result.get_url(n)
		title = self.result.get_title(n)
		dlg = DownloadProgress(wx.GetApp().GetTopWindow(), title)
		direct_download(2, url, dlg, "video", os.path.join(config_get("path"), self.title))

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
		self.videosBox.SetFocus()
	def back(self):
		self.Parent.Show()
		self.Destroy()

	def onHook(self, event):
		if event.KeyCode == wx.WXK_ESCAPE and not type(self.FindFocus()) == MediaGui:
			self.back()
		else:
			event.Skip()