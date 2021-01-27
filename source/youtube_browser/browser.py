import webbrowser
from threading import Thread

import pafy
import pyperclip
import wx
from dialogs.download_progress import DownloadProgress
from dialogs.search_dialog import SearchDialog
from dialogs.settings_dialog import SettingsDialog
from download_handler.downloader import downloadAction
from language_handler import init_translation
from media_player.media_gui import MediaGui
from media_player.player import Player
from nvda_client.client import speak
from settings_handler import config_get

from youtube_browser.search_handler import Search

try:
	init_translation("accessible_youtube_downloader")
except:
	_ = lambda msg: msg



class YoutubeBrowser(wx.Frame):
	def __init__(self, parent):
		wx.Frame.__init__(self, parent=parent, title=parent.Title)
		self.Centre()
		self.Maximize(True)
		self.panel = wx.Panel(self)
		lbl = wx.StaticText(self.panel, -1, _("نتائج البحث: "))
		self.searchResults = wx.ListBox(self.panel, -1, choices=[])
		self.loadMoreButton = wx.Button(self.panel, -1, _("تحميل المزيد من النتائج"))
		self.loadMoreButton.Enabled = False
		self.loadMoreButton.Show(not config_get("autoload"))
		playButton = wx.Button(self.panel, -1, _("تشغيل (enter)"), name="controls")
		self.downloadButton = wx.Button(self.panel, -1, _("تنزيل"), name="controls")
		searchButton = wx.Button(self.panel, -1, _("بحث... (ctrl+f)"))
		backButton = wx.Button(self.panel, -1, _("العودة إلى النافذة الرئيسية"))
		sizer = wx.BoxSizer(wx.VERTICAL)
		sizer1 = wx.BoxSizer(wx.HORIZONTAL)
		sizer1.Add(backButton, 1, wx.ALL)
		sizer1.Add(searchButton, 1, wx.ALL)
		sizer2 = wx.BoxSizer(wx.HORIZONTAL)
		for control in self.panel.GetChildren():
			if control.Name == "controls":
				sizer2.Add(control, 1)
			control.Bind(wx.EVT_KEY_DOWN, self.onKeyDown)
		sizer.Add(sizer1, 1, wx.EXPAND)
		sizer.Add(lbl, 1, wx.ALL)
		sizer.Add(self.searchResults, 1, wx.EXPAND)
		sizer.Add(self.loadMoreButton, 1)
		sizer.Add(sizer2, 1)
		self.panel.SetSizer(sizer)
		self.contextSetup()
		menuBar = wx.MenuBar()
		optionsMenu = wx.Menu()
		settingsItem = optionsMenu.Append(-1, _("الإعدادات...\tctrl+alt+s"))
		menuBar.Append(optionsMenu, _("خيارات"))
		self.SetMenuBar(menuBar)
		self.Bind(wx.EVT_MENU, lambda event: SettingsDialog(self), settingsItem)
		self.loadMoreButton.Bind(wx.EVT_BUTTON, self.onLoadMore)
		playButton.Bind(wx.EVT_BUTTON, lambda event: self.playVideo())
		self.downloadButton.Bind(wx.EVT_BUTTON, self.onDownload)
		searchButton.Bind(wx.EVT_BUTTON, self.onSearch)
		backButton.Bind(wx.EVT_BUTTON, lambda event: self.backAction())
		self.searchResults.Bind(wx.EVT_CHAR_HOOK, self.onResultsClick)
		self.Bind(wx.EVT_LISTBOX_DCLICK, lambda event: self.playVideo(), self.searchResults)
		self.searchResults.Bind(wx.EVT_LISTBOX, self.onListBox)
		self.Bind(wx.EVT_CLOSE, lambda event: wx.Exit())
		self.Show()
		self.Parent.Hide()
		self.searchAction()
	def searchAction(self, value=""):
		dialog = SearchDialog(self, value=value)
		query = dialog.query
		filter = dialog.filter
		if query is None:
			self.togleControls()
			return
		try:
			self.search = Search(query, filter)
		except:
			wx.MessageBox("تعذر إجراء عملية البحث بسبب خطأ غير معروف. تأكد من وجود اتصال جيد بالشبكة ثم عاود المحاولة. إذا استمرت المشكلة, قم بإعادة تشغيل البرنامج.", "خطأ", style=wx.ICON_ERROR)
			self.togleControls()
			return
		titles = self.search.get_titles()
		self.searchResults.Set(titles)
		self.togleControls()
		try:
			self.searchResults.SetSelection(0)
		except:
			pass
		self.searchResults.SetFocus()
		self.togleDownload()

	def onSearch(self, event):
		try:
			self.searchAction(self.search.query)
		except AttributeError:
			self.searchAction("")
	def playVideo(self):
		number = self.searchResults.Selection
		title = self.search.get_title(number)
		url = self.search.get_url(number)
		speak(_("جاري التشغيل"))
		media = pafy.new(url)
		gui = MediaGui(self, title, url, True if self.search.get_views(number) is not None else False)
		stream = media.getbest()
		self.Hide()
		gui.Show()
		gui.player = Player(stream.url, gui.GetHandle())
	def playAudio(self):
		number = self.searchResults.Selection
		title = self.search.get_title(number)
		url = self.search.get_url(number)
		speak(_("جاري التشغيل"))
		media = pafy.new(url)
		gui = MediaGui(self, title, url)
		stream = media.getbestaudio()
		self.Hide()
		gui.Show()
		gui.player = Player(stream.url, gui.GetHandle())

	def onResultsClick(self, event):
		if event.GetKeyCode() == wx.WXK_RETURN:
			self.playVideo()
		event.Skip()
	def contextSetup(self):
		self.contextMenu = wx.Menu()
		videoPlayItem = self.contextMenu.Append(-1, _("تشغيل"))
		audioPlayItem = self.contextMenu.Append(-1, _("التشغيل كمقطع صوتي"))
		self.downloadMenu = wx.Menu()
		videoItem = self.downloadMenu.Append(-1, _("فيديو"))
		audioMenu = wx.Menu()
		m4aItem = audioMenu.Append(-1, "m4a")
		mp3Item = audioMenu.Append(-1, "mp3")
		self.downloadMenu.Append(-1, _("صوت"), audioMenu)
		self.downloadId = wx.NewId()
		self.contextMenu.Append(self.downloadId, _("تنزيل"), self.downloadMenu)
		copyItem = self.contextMenu.Append(-1, _("نسخ رابط المقطع"))
		webbrowserItem = self.contextMenu.Append(-1, _("الفتح من خلال متصفح الإنترنت"))
		self.searchResults.Bind(wx.EVT_MENU, lambda event: self.playVideo(), videoPlayItem)
		self.searchResults.Bind(wx.EVT_MENU, lambda event: self.playAudio(), audioPlayItem)
		self.searchResults.Bind(wx.EVT_MENU, self.onCopy, copyItem)
		self.searchResults.Bind(wx.EVT_CONTEXT_MENU, lambda event: self.searchResults.PopupMenu(self.contextMenu))
		self.Bind(wx.EVT_MENU, self.onVideoDownload, videoItem)
		self.Bind(wx.EVT_MENU, self.onM4aDownload, m4aItem)
		self.Bind(wx.EVT_MENU, self.onMp3Download, mp3Item)

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

	def onM4aDownload(self, event):
		url = self.search.get_url(self.searchResults.Selection)
		title = self.search.get_title(self.searchResults.Selection)
		dlg = DownloadProgress(self, title)
		path = config_get("path")
		t = Thread(target=downloadAction, args=[url, path, dlg, "bestaudio[ext=m4a]", dlg.gaugeProgress, dlg.textProgress])
		t.start()

	def onMp3Download(self, event):
		url = self.search.get_url(self.searchResults.Selection)
		title = self.search.get_title(self.searchResults.Selection)
		dlg = DownloadProgress(self, title)
		path = config_get("path")
		t = Thread(target=downloadAction, args=[url, path, dlg, "bestaudio[ext=m4a]", dlg.gaugeProgress, dlg.textProgress, True])
		t.start()

	def onVideoDownload(self, event):
		url = self.search.get_url(self.searchResults.Selection)
		title = self.search.get_title(self.searchResults.Selection)
		dlg = DownloadProgress(self, title)
		path = config_get("path")
		t = Thread(target=downloadAction, args=[url, path, dlg, "bestvideo[ext=mp4]+bestaudio[ext=m4a]/mp4", dlg.gaugeProgress, dlg.textProgress])
		t.start()

	def onCopy(self, event):
		pyperclip.copy(self.search.get_url(self.searchResults.Selection))
		wx.MessageBox(_("تم نسخ رابط المقطع بنجاح"), _("اكتمال"), parent=self)
	def loadMore(self):
		if self.searchResults.Strings == []:
			return
		speak(_("جاري تحميل المزيد من النتائج"))
		if self.search.load_more() is None:
			speak(_("لم يتمكن البرنامج من تحميل المزيد من النتائج"))
			return
		# position = self.searchResults.Selection
		wx.CallAfter(self.searchResults.Append, self.search.get_last_titles())
		speak(_("تم تحميل المزيد من نتائج البحث"))
		wx.CallAfter(self.searchResults.SetFocus)
	def onListBox(self, event):
		self.togleDownload()
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
		if self.search.get_views(n) is None:
			self.contextMenu.Enable(self.downloadId, False)
			self.downloadButton.Enabled = False
		else:
			self.contextMenu.Enable(self.downloadId, True)
			self.downloadButton.Enabled = True

	def onKeyDown(self, event):
		if event.controlDown and event.KeyCode == ord("F"):
			self.onSearch(None)
		event.Skip()