import webbrowser
import os
os.add_dll_directory(os.getcwd())
import pyperclip
import wx
from dialogs.download_progress import DownloadProgress
from download_handler.downloader import downloadAction
from nvda_client.client import speak
from settings_handler import config_get, config_set
import application
from utiles import direct_download
from vlc import State
from dialogs.settings_dialog import SettingsDialog

class CustomeButton(wx.Button):
	def __init__(self, parent, id, label, name=""):
		wx.Button.__init__(self, parent, id, label, name=name)
	def AcceptsFocusFromKeyboard(self):
		return False

class MediaGui(wx.Frame):
	def __init__(self, parent, title, url, can_download=True):
		wx.Frame.__init__(self, parent, title=f'{title} - {application.name}')
		self.stream = not can_download
		self.seek = int(config_get("seek"))
		self.Centre()
		self.Maximize(True)
		self.SetBackgroundColour(wx.BLACK)
		self.player = None
		self.url = url
		beginingButton = CustomeButton(self, -1, _("بداية المقطع"), "controls")
		rewindButton = CustomeButton(self, -1, _("إرجاع المقطع <"), "controls")
		playButton = CustomeButton(self, -1, _("تشغيل\إيقاف"), "controls")
		forwardButton = CustomeButton(self, -1, _("تقديم المقطع >"), "controls")
		sizer = wx.BoxSizer(wx.VERTICAL)
		sizer1 = wx.BoxSizer(wx.HORIZONTAL)
		for control in self.GetChildren():
			if control.Name == "controls":
				sizer1.Add(control, 1)
		sizer.AddStretchSpacer()
		sizer.Add(sizer1)
		self.SetSizer(sizer)
		menuBar = wx.MenuBar()
		trackOptions = wx.Menu()
		downloadMenu = wx.Menu()
		downloadId = wx.NewId()
		videoItem = downloadMenu.Append(-1, _("فيديو"))
		audioMenu = wx.Menu()
		m4aItem = audioMenu.Append(-1, "m4a")
		mp3Item = audioMenu.Append(-1, "mp3")
		downloadMenu.Append(-1, _("صوت"), audioMenu)
		trackOptions.Append(downloadId, _("تنزيل"), downloadMenu)
		trackOptions.Enable(downloadId, can_download)
		directDownloadItem = trackOptions.Append(-1, _("التنزيل المباشر...\tctrl+d"))
		directDownloadItem.Enable(can_download)
		copyItem = trackOptions.Append(-1, _("نسخ رابط المقطع\tctrl+l"))
		browserItem = trackOptions.Append(-1, _("الفتح من خلال متصفح الإنترنت\tctrl+b"))
		settingsItem = trackOptions.Append(-1, _("الإعدادات.\talt+s"))
		menuBar.Append(trackOptions, _("خيارات المقطع"))
		self.SetMenuBar(menuBar)
		self.Bind(wx.EVT_MENU, self.onVideoDownload, videoItem)
		self.Bind(wx.EVT_MENU, self.onM4aDownload, m4aItem)
		self.Bind(wx.EVT_MENU, self.onMp3Download, mp3Item)
		self.Bind(wx.EVT_MENU, self.onDirect, directDownloadItem)
		self.Bind(wx.EVT_MENU, self.onCopy, copyItem)
		self.Bind(wx.EVT_MENU, self.onBrowser, browserItem)
		self.Bind(wx.EVT_MENU, lambda event: SettingsDialog(self), settingsItem)
		self.Bind(wx.EVT_KEY_DOWN, self.onKeyDown)
		for control in self.GetChildren():
			control.Bind(wx.EVT_KEY_DOWN, self.onKeyDown)
		beginingButton.Bind(wx.EVT_BUTTON, lambda event: self.beginingAction())
		rewindButton.Bind(wx.EVT_BUTTON, lambda event: self.rewindAction())
		playButton.Bind(wx.EVT_BUTTON, lambda event: self.playAction())
		forwardButton.Bind(wx.EVT_BUTTON, lambda event: self.forwardAction())
		self.Bind(wx.EVT_CLOSE, lambda event: self.closeAction())
	def playAction(self):
		state = self.player.media.get_state()
		if state in (State.NothingSpecial, State.Stopped):
			self.player.media.play()
		elif state in (State.Playing, State.Paused):
			if not self.stream:
				self.player.media.pause()
			else: 
				self.player.media.stop()
	def forwardAction(self):
		if self.player is None:
			return
		position = self.player.media.get_position()
		self.player.media.set_position(position+self.player.seek(self.seek))
	def rewindAction(self):
		if self.player is None:
			return
		position = self.player.media.get_position()
		self.player.media.set_position(position-self.player.seek(self.seek))
	def beginingAction(self):
		if self.player is None:
			return
		self.player.media.set_position(0.0)
		speak(_("بداية المقطع"))
	def closeAction(self):
		if self.player is not None:
			self.player.media.stop()
		self.GetParent().Show()
		self.Destroy()

	def onKeyDown(self, event):
		if event.GetKeyCode() == wx.WXK_SPACE:
			self.playAction()
		elif event.GetKeyCode() == wx.WXK_RIGHT:
			self.forwardAction()
		elif event.GetKeyCode() == wx.WXK_LEFT:
			self.rewindAction()
		elif event.GetKeyCode() == wx.WXK_UP:
			if self.player is None:
				event.Skip()
				return
			volume = self.player.media.audio_get_volume()
			self.player.media.audio_set_volume(volume+5)
			speak(f"{self.player.media.audio_get_volume()} {_('بالمائة')}")
		elif event.GetKeyCode() == wx.WXK_DOWN:
			if self.player is None:
				event.Skip()
				return
			volume = self.player.media.audio_get_volume()
			self.player.media.audio_set_volume(volume-5)
			speak(f"{self.player.media.audio_get_volume()} {_('بالمائة')}")
		elif event.GetKeyCode() == wx.WXK_HOME:
			self.beginingAction()
		elif event.controlDown and event.shiftDown and event.KeyCode == ord("D"):
			if self.player is not None:
				speak(_("المدة: {}").format(self.player.get_duration()))
		elif event.controlDown and event.shiftDown and event.KeyCode == ord("T"):
			if self.player is not None:
				speak(_("الوقت المنقضي: {}").format(self.player.get_elapsed()))
		elif event.KeyCode == ord("S"):

			if self.player is not None:
				self.player.media.set_rate(1.4)
				speak(_("سريع"))
		elif event.KeyCode == ord("D"):
			if self.player is not None:
				self.player.media.set_rate(1.0)
				speak(_("معتدل"))
		elif event.KeyCode == ord("F"):
			if self.player is not None:
				self.player.media.set_rate(0.6)
				speak(_("بطيء"))
		elif event.GetKeyCode() in (ord("-"), wx.WXK_NUMPAD_SUBTRACT):
			self.seek -= 1
			if self.seek < 1:
				self.seek = 1
			speak("{} {} {}".format(_("تحريك المقطع"), self.seek, _("ثانية/ثواني")))
			config_set("seek", self.seek)
		elif event.GetKeyCode() in (ord("="), wx.WXK_NUMPAD_ADD):
			self.seek += 1
			if self.seek > 10:
				self.seek = 10
			speak("{} {} {}".format(_("تحريك المقطع"), self.seek, _("ثانية/ثواني")))
			config_set("seek", self.seek)
		elif event.GetKeyCode() == wx.WXK_ESCAPE:
			self.closeAction()
		event.Skip()
	def onCopy(self, event):
		pyperclip.copy(self.url)
		wx.MessageBox(_("تم نسخ رابط المقطع بنجاح"), _("اكتمال"), parent=self)
	def onBrowser(self, event):
		speak(_("جاري الفتح"))
		webbrowser.open(self.url)

	def onM4aDownload(self, event):
		dlg = DownloadProgress(self.Parent)
		direct_download(1, self.url, dlg)

	def onMp3Download(self, event):
		dlg = DownloadProgress(self.Parent)
		direct_download(2, self.url, dlg)

	def onVideoDownload(self, event):
		dlg = DownloadProgress(self.Parent)
		direct_download(0, self.url, dlg)


	def onDirect(self, event):
		dlg = DownloadProgress(self.Parent)
		direct_download(int(config_get('defaultformat')), self.url, dlg)
