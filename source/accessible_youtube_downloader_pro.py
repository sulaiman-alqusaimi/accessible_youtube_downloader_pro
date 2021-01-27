import re
import application
import pafy
import pyperclip
import wx
import os
import subprocess

import settings_handler
from dialogs.auto_detect_dialog import AutoDetectDialog
from dialogs.download_dialog import DownloadDialog
from dialogs.link_dlg import LinkDlg
from dialogs.settings_dialog import SettingsDialog
from dialogs.text_viewer import Viewer
from doc_handler import documentation_get
from language_handler import init_translation
from media_player.media_gui import MediaGui
from media_player.player import Player
from youtube_browser.browser import YoutubeBrowser

settings_handler.config_initialization()

try:
	init_translation("accessible_youtube_downloader")
except:
	_ = lambda msg: msg

class CustomLabel(wx.StaticText):
	def __init__(self, parent, id, label, name=""):
		wx.StaticText.__init__(self, parent, id, label, name=name)
	def AcceptsFocusFromKeyboard(self):
		return True

class HomeScreen(wx.Frame):
	def __init__(self):
		wx.Frame.__init__(self, parent=None, title=application.name)
		self.Centre()
		self.Maximize(True)
		panel = wx.Panel(self)
		self.instruction = CustomLabel(panel, -1, _("اضغط على مفتاح القوائم alt للوصول إلى خيارات البرنامج, أو تنقل بزر التاب للوصول سريعًا إلى أهم الخيارات المتاحة."))
		youtubeBrowseButton = wx.Button(panel, -1, _("البحث في youtube\tctrl+f"), name="tab")
		downloadFromLinkButton = wx.Button(panel, -1, _("التنزيل من خلال رابط\tctrl+d"), name="tab")
		playYoutubeLinkButton = wx.Button(panel, -1, _("تشغيل فيديو youtube من خلال الرابط\tctrl+y"), name="tab")
		sizer = wx.BoxSizer(wx.VERTICAL)
		sizer1 = wx.BoxSizer(wx.HORIZONTAL)
		for control in panel.GetChildren():
			if control.Name == "tab":
				sizer1.Add(control, 1)
		sizer.Add(self.instruction, 1)
		sizer.AddStretchSpacer()
		sizer.Add(sizer1, 1, wx.EXPAND)
		panel.SetSizer(sizer)
		menuBar = wx.MenuBar()
		mainMenu = wx.Menu()
		searchItem = mainMenu.Append(-1, _("البحث في youtube\tctrl+f"))
		downloadItem = mainMenu.Append(-1, _("التنزيل من خلال رابط\tctrl+d"))
		playItem = mainMenu.Append(-1, _("تشغيل فيديو youtube من خلال الرابط\tctrl+y"))
		openDownloadingPathItem = mainMenu.Append(-1, _("فتح مجلد التنزيل\tctrl+p"))
		settingsItem = mainMenu.Append(-1, _("الإعدادات...\tctrl+alt+s"))
		exitItem = mainMenu.Append(-1, _("خروج\tctrl+w"))
		menuBar.Append(mainMenu, _("القائمة الرئيسية"))
		aboutMenu = wx.Menu()
		userGuideItem = aboutMenu.Append(-1, _("دليل المستخدم...\tf1"))
		aboutItem = aboutMenu.Append(-1, _("عن البرنامج..."))
		menuBar.Append(aboutMenu, _("حول"))
		self.SetMenuBar(menuBar)
		# event bindings
		self.Bind(wx.EVT_MENU, self.onSearch, searchItem)
		youtubeBrowseButton.Bind(wx.EVT_BUTTON, self.onSearch)
		self.Bind(wx.EVT_MENU, self.onDownload, downloadItem)
		downloadFromLinkButton.Bind(wx.EVT_BUTTON, self.onDownload)
		self.Bind(wx.EVT_MENU, self.onPlay, playItem)
		playYoutubeLinkButton.Bind(wx.EVT_BUTTON, self.onPlay)
		self.Bind(wx.EVT_MENU, self.onOpen, openDownloadingPathItem)
		self.Bind(wx.EVT_MENU, lambda event: SettingsDialog(self), settingsItem)
		self.Bind(wx.EVT_MENU, lambda event: wx.Exit(), exitItem)
		self.Bind(wx.EVT_MENU, self.onGuide, userGuideItem)
		self.Bind(wx.EVT_MENU, self.onAbout, aboutItem)
		self.Bind(wx.EVT_CHAR_HOOK, self.onHook)
		self.Show()
		self.detectFromClipboard(settings_handler.config_get("autodetect"))
	def onPlay(self, event):
		linkDlg = LinkDlg(self)
		data = linkDlg.data
		media = pafy.new(data["link"])
		gui = MediaGui(self, media.title, data["link"])
		stream = media.getbest() if not data["audio"] else media.getbestaudio()
		self.Hide()
		gui.Show()
		gui.player = Player(stream.url, gui.GetHandle())
	def onDownload(self, event):
		dlg = DownloadDialog(self)
		dlg.Show()
	def onSearch(self, event):
		browser = YoutubeBrowser(self)
	def detectFromClipboard(self, config):
		if not config:
			return
		clip_content = pyperclip.paste() # get the clipboard content
		pattern = re.compile("^((?:https?:)?\/\/)?((?:www|m)\.)?((?:youtube\.com|youtu.be))(\/(?:[\w\-]+\?v=|embed\/|v\/)?)([\w\-]+)(\S+)?$") # youtube links regular expression pattern
		match = pattern.search(clip_content) # search in the clipboard content to the specified pattern
		if match is not None:
			AutoDetectDialog(self, clip_content)
	def onOpen(self, event):
		path = settings_handler.config_get("path")
		if not os.path.exists(path):
			os.mkdir(path)
		explorer = os.path.join(os.getenv("SYSTEMDRIVE"), "\\windows\\explorer")
		subprocess.call(f"{explorer} {path}")
	def onHook(self, event):
		if event.KeyCode == wx.WXK_F1:
			content = documentation_get()
			if content is None:
				event.Skip()
				return
			Viewer(self, _("دليل استخدام برنامج accessible youtube downloader pro"), content)
		event.Skip()
	def onGuide(self, event):
		content = documentation_get()
		if content is None:
			return
		Viewer(self, _("دليل استخدام برنامج accessible youtube downloader pro"), content)
	def onAbout(self, event):
		about = f"""{_('اسم البرنامج')}: {application.name}.
{_('الإصدار')}: {application.version}.
{_('طُوِر بواسطة')}: {_(application.author)}.
{_('الوصف')}: {_(application.describtion)}."""
		wx.MessageBox(about, _("حول"), parent=self)

app = wx.App()
HomeScreen()
app.MainLoop()
