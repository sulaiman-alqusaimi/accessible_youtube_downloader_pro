
# the main module 
import sys
import os
os.chdir	(os.path.abspath(os.path.dirname(__file__)))
os.add_dll_directory(os.getcwd())
import settings_handler
settings_handler.config_initialization() # calling the config_initialization function which sets up the accessible_youtube_downloader_pro.ini file in the user appdata folder
from app_logger import get_logger, install_exception_logging
install_exception_logging()
logger = get_logger()
logger.info("Starting application")
import database
import application
import pyperclip
import wx
import webbrowser

import subprocess
from utiles import youtube_regexp, check_for_updates, get_audio_stream, get_video_stream
from nvda_client.client import speak

from gui.activity_dialog import LoadingDialog
from gui.auto_detect_dialog import AutoDetectDialog
from gui.download_dialog import DownloadDialog
from gui.link_dlg import LinkDlg
from gui.settings_dialog import SettingsDialog
from gui.text_viewer import Viewer
from gui.custom_controls import CustomLabel
from gui.favorites import Favorites
from doc_handler import documentation_get
from language_handler import init_translation, codes
from media_player.media_gui import MediaGui
from media_player.player import Player
from youtube_browser.browser import YoutubeBrowser
from threading import Thread



settings_handler.config_initialization() # calling the config_initialization function which sets up the accessible_youtube_downloader_pro.ini file in the user appdata folder
init_translation("accessible_youtube_downloader") # program localization




class HomeScreen(wx.Frame):
	# the main class
	def __init__(self):
		wx.Frame.__init__(self, parent=None, title=application.name)
		self.Centre()
		self.SetSize(wx.DisplaySize())
		self.Maximize(True)
		panel = wx.Panel(self)
		self.instruction = CustomLabel(panel, -1, _("press the alt key to go through the available options, or use the tab key for quick access.")) # a breafe instruction message witch is shown by the custome StaticText to automaticly be focused when launching the app
		youtubeBrowseButton = wx.Button(panel, -1, _("Search in youtube\tctrl+f"), name="tab")
		downloadFromLinkButton = wx.Button(panel, -1, _("download YouTube link\tctrl+d"), name="tab")
		playYoutubeLinkButton = wx.Button(panel, -1, _("play YouTube link\tctrl+y"), name="tab")
		favButton = wx.Button(panel, -1, _("favorite videos\tctrl+shift+f"), name="tab")
		# quick access buttons
		sizer = wx.BoxSizer(wx.VERTICAL) # the main sizer
		sizer1 = wx.BoxSizer(wx.HORIZONTAL) # quick access buttons sizer
		for control in panel.GetChildren():
			if control.Name == "tab":
				sizer1.Add(control, 1) # adding quick access buttons using for loop sins that eatch button named by the "tab" word
		sizer.Add(self.instruction, 1)
		sizer.AddStretchSpacer()
		sizer.Add(sizer1, 1, wx.EXPAND)
		panel.SetSizer(sizer) # adding the sizer to the main panel
		menuBar = wx.MenuBar() # seting up the menu bar
		mainMenu = wx.Menu()
		searchItem = mainMenu.Append(-1, _("Search in youtube\tctrl+f")) # search in youtube item
		downloadItem = mainMenu.Append(-1, _("download YouTube link\tctrl+d"))# download link item
		playItem = mainMenu.Append(-1, _("play YouTube link\tctrl+y")) # play youtube link item
		favoriteItem = mainMenu.Append(-1, _("favorite videos\tctrl+shift+f"))
		openDownloadingPathItem = mainMenu.Append(-1, _("open downloading folder\tctrl+p")) # open downloading folder item
		settingsItem = mainMenu.Append(-1, _("settings...\talt+s")) # settings item
		exitItem = mainMenu.Append(-1, _("exit\tctrl+w")) # quit item
		hotKeys = wx.AcceleratorTable([
			(wx.ACCEL_CTRL, ord("F"), searchItem.GetId()),
			(wx.ACCEL_CTRL, ord("D"), downloadItem.GetId()),
			(wx.ACCEL_CTRL, ord("Y"), playItem.GetId()),
			(wx.ACCEL_CTRL+wx.ACCEL_SHIFT, ord("F"), favoriteItem.GetId()),
			(wx.ACCEL_CTRL, ord("P"), openDownloadingPathItem.GetId()),
			(wx.ACCEL_ALT, ord("S"), settingsItem.GetId()),
			(wx.ACCEL_CTRL, ord("W"), exitItem.GetId())
		])
		# the accelerator table asociated with the menu items
		self.SetAcceleratorTable(hotKeys) # adding the accelerator table to the frame
		menuBar.Append(mainMenu, _("main menu")) # append the main menu to the menu bar
		aboutMenu = wx.Menu()
		userGuideItem = aboutMenu.Append(-1, _("userguide\u2026\tf1")) # userguide
		checkForUpdatesItem = aboutMenu.Append(-1, _("search for updates"))
		aboutItem = aboutMenu.Append(-1, _("about the app...")) # about item
		contactMenu = wx.Menu()
		emailItem = contactMenu.Append(-1, _("email..."))
		twitterItem = contactMenu.Append(-1, _("twitter..."))
		aboutMenu.AppendSubMenu(contactMenu, _("contact with me"))
		menuBar.Append(aboutMenu, _("about")) # append the about menu to the menu bar
		self.SetMenuBar(menuBar) # add the menu bar to the window
		# event bindings
		self.Bind(wx.EVT_MENU, self.onSearch, searchItem)
		youtubeBrowseButton.Bind(wx.EVT_BUTTON, self.onSearch)
		self.Bind(wx.EVT_MENU, self.onDownload, downloadItem)
		downloadFromLinkButton.Bind(wx.EVT_BUTTON, self.onDownload)
		self.Bind(wx.EVT_MENU, self.onPlay, playItem)
		playYoutubeLinkButton.Bind(wx.EVT_BUTTON, self.onPlay)
		self.Bind(wx.EVT_MENU, self.onFavorite, favoriteItem)
		favButton.Bind(wx.EVT_BUTTON, self.onFavorite)
		self.Bind(wx.EVT_MENU, self.onOpen, openDownloadingPathItem)
		self.Bind(wx.EVT_MENU, lambda event: SettingsDialog(self), settingsItem)
		self.Bind(wx.EVT_MENU, lambda event: wx.Exit(), exitItem)
		self.Bind(wx.EVT_MENU, self.onGuide, userGuideItem)
		self.Bind(wx.EVT_MENU, self.onCheckForUpdates, checkForUpdatesItem)
		self.Bind(wx.EVT_MENU, self.onAbout, aboutItem)
		self.Bind(wx.EVT_MENU, lambda event: webbrowser.open("mailto:Suleiman.alqusaimi@gmail.com"), emailItem)
		self.Bind(wx.EVT_MENU, lambda event: webbrowser.open("https://twitter.com/suleiman3ahmed"), twitterItem)
		self.Bind(wx.EVT_CHAR_HOOK, self.onHook)
		self.Bind(wx.EVT_SHOW, self.onShow)
		self.Bind(wx.EVT_CLOSE, self.onClose)
		self.Show()
		self.detectFromClipboard(settings_handler.config_get("autodetect"))
		if settings_handler.config_get("checkupdates"):
			Thread(target=check_for_updates, args=[True]).start()
	def onPlay(self, event): # the event function called when the play youtube link is clicked
		linkDlg = LinkDlg(self)
		data = linkDlg.data # get the link and playing format from the dialog
		url = data["link"]
		logger.info("Opening link in media player. audio=%s url=%s", data["audio"], url)
		stream = LoadingDialog(self, _("playing"), get_video_stream if not data["audio"] else get_audio_stream, url).res
		gui = MediaGui(self, stream.title, stream, data["link"]) # initiating the media gui
		self.Hide()

	def onDownload(self, event): # the event function for the link downloading item to show the appropriate dialog
		logger.info("Opening download dialog")
		dlg = DownloadDialog(self)
		dlg.Show()
	def onSearch(self, event): # showing the youtube browser window event function
		logger.info("Opening YouTube browser")
		browser = YoutubeBrowser(self)
	def detectFromClipboard(self, config):
		if not config:
			return
		clip_content = pyperclip.paste() # get the clipboard content
		match = youtube_regexp(clip_content)
		if match is not None:
			AutoDetectDialog(self, clip_content)
	def onFavorite(self, event):
		logger.info("Opening favorites")
		Favorites(self)
		self.Hide()
	def onOpen(self, event):
		path = settings_handler.config_get("path")
		logger.info("Opening download path: %s", path)
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
			Viewer(self, _("accessible YouTube  downloader pro userguide"), content)
		event.Skip()
	def onShow(self, event):
		self.instruction.SetFocus()
	def onGuide(self, event):
		content = documentation_get()
		if content is None:
			return
		Viewer(self, _("accessible YouTube  downloader pro userguide"), content).ShowModal()
	def onCheckForUpdates(self, event):
		from gui.activity_dialog import LoadingDialog
		# speak(_("checking for updates. please wait"))
		logger.info("Manual update check requested")
		LoadingDialog(self, _("Checking for updates. Please wait."), check_for_updates)
		self.instruction.SetFocus()

	def onAbout(self, event):
		about = f"""{_("app name")}: {application.name}.
{_("version")}: {application.version}.
{_("developed by")}: {application.author}.
{_("description: ")}{_(application.describtion)}."""
		wx.MessageBox(about, _("about"), parent=self)
	def onClose(self, event):
		logger.info("Closing application")
		database.disconnect()
		wx.Exit()

app = wx.App()
lang_id = codes.get(settings_handler.config_get("lang"), wx.LANGUAGE_ARABIC)
locale = wx.Locale(lang_id)
HomeScreen()
app.MainLoop()
