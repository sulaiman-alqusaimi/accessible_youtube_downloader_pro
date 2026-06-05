import os
import sys

import wx
from settings_handler import config_get, config_set
from language_handler import supported_languages
from app_logger import get_logger


logger = get_logger()
languages = {index:language for language, index in enumerate(supported_languages.values())}
cookie_browser_values = ["none", "chrome", "edge", "firefox", "brave", "opera", "vivaldi", "chromium"]

class SettingsDialog(wx.Dialog):
	def __init__(self, parent):
		wx.Dialog.__init__(self, parent, title=_("settings"))
		self.SetSize(500, 500)
		self.Centre()
		self.preferences = {}
		panel = wx.Panel(self)
		lbl = wx.StaticText(panel, -1, _("program's display language: "), name="language")
		self.languageBox = wx.Choice(panel, -1, name="language")
		self.languageBox.Set([_(language) for language in supported_languages.keys()])
		try:
			self.languageBox.Selection = languages[config_get("lang")]
		except KeyError:
			self.languageBox.Selection = 0
		lbl1 = wx.StaticText(panel, -1, _("download folder path: "), name="path")
		self.pathField = wx.TextCtrl(panel, -1, value=config_get("path"), name="path", style=wx.TE_READONLY|wx.TE_MULTILINE|wx.HSCROLL)
		changeButton = wx.Button(panel, -1, _("change path"), name="path")
		preferencesBox = wx.StaticBox(panel, -1, _("general preferences"))
		self.autoDetectItem = wx.CheckBox(preferencesBox, -1, _("automaticly detect YouTube links when launching the program"), name="autodetect")
		self.autoCheckForUpdates = wx.CheckBox(preferencesBox, -1, _("automatically check for new update when starting the program"), name="checkupdates")
		self.autoLoadItem = wx.CheckBox(preferencesBox, -1, _("automaticly load more results when reatching the end of the videos list"), name="autoload")
		self.autoCheckForUpdates.SetValue(config_get("checkupdates"))
		self.autoDetectItem.SetValue(config_get("autodetect"))
		self.autoLoadItem.SetValue(config_get("autoload"))
		downloadPreferencesBox = wx.StaticBox(panel, -1, _("download settings"))
		lbl2 = wx.StaticText(downloadPreferencesBox, -1, _("direct downloading format: "))
		self.formats = wx.Choice(downloadPreferencesBox, -1, choices=[_("mp4 video"), _("m4a audio"), _("mp3 audio")])
		self.formats.Selection = int(config_get('defaultformat'))
		lbl3 = wx.StaticText(downloadPreferencesBox, -1, _("mp3 conversion quality: "))
		self.mp3Quality = wx.Choice(downloadPreferencesBox, -1, choices=["96 kbps", "128 kbps", "192 kbps"], name="conversion")
		self.mp3Quality.Selection = int(config_get("conversion"))
		lbl4 = wx.StaticText(downloadPreferencesBox, -1, _("YouTube cookies from browser: "))
		cookie_browser_labels = [_("Do not use cookies"), "Chrome", "Edge", "Firefox", "Brave", "Opera", "Vivaldi", "Chromium"]
		self.cookiesBrowser = wx.Choice(downloadPreferencesBox, -1, choices=cookie_browser_labels, name="cookiesfrombrowser")
		try:
			self.cookiesBrowser.Selection = cookie_browser_values.index(config_get("cookiesfrombrowser"))
		except ValueError:
			self.cookiesBrowser.Selection = 0
		playerOptions = wx.StaticBox(panel, -1, _("player options"))
		self.continueWatching = wx.CheckBox(playerOptions, -1, _("continue where you left the video when open it again"), name="continue")
		self.continueWatching.Value = config_get("continue")
		self.repeateTracks = wx.CheckBox(playerOptions, -1, _("automaticly replay tracks while its end is reatched"), name="repeatetracks")
		self.autoPlayNext = wx.CheckBox(playerOptions, -1, _("automatically play the next track when the current video ends"), name="autonext")
		self.autoPlayNext.Value = config_get('autonext')
		self.repeateTracks.Value = config_get("repeatetracks")
		okButton = wx.Button(panel, wx.ID_OK, _("&ok"), name="ok_cancel")
		okButton.SetDefault()
		cancelButton = wx.Button(panel, wx.ID_CANCEL, _("&cancel"), name="ok_cancel")
		sizer = wx.BoxSizer(wx.VERTICAL)
		sizer1 = wx.BoxSizer(wx.HORIZONTAL)
		sizer2 = wx.BoxSizer(wx.HORIZONTAL)
		sizer3 = wx.BoxSizer(wx.HORIZONTAL)
		sizer4 = wx.BoxSizer(wx.VERTICAL)
		sizer5 = wx.BoxSizer(wx.HORIZONTAL)
		sizer6 = wx.BoxSizer(wx.HORIZONTAL)
		sizer7 = wx.BoxSizer(wx.HORIZONTAL)
		okCancelSizer = wx.BoxSizer(wx.HORIZONTAL)
		sizer1.Add(lbl, 1)
		sizer1.Add(self.languageBox, 1, wx.EXPAND)
		for control in panel.GetChildren():
			if control.Name == "ok_cancel":
				okCancelSizer.Add(control, 1)
			elif control.Name == "path":
				sizer2.Add(control, 1)
		for item in preferencesBox.GetChildren():
			sizer3.Add(item, 1)
		preferencesBox.SetSizer(sizer3)
		sizer5.Add(lbl3, 1)
		sizer5.Add(self.mp3Quality, 1)
		sizer6.Add(lbl2, 1)
		sizer6.Add(self.formats, 1)
		cookiesSizer = wx.BoxSizer(wx.HORIZONTAL)
		cookiesSizer.Add(lbl4, 1)
		cookiesSizer.Add(self.cookiesBrowser, 1)
		sizer4.Add(sizer5)
		sizer4.Add(sizer6)
		sizer4.Add(cookiesSizer)
		downloadPreferencesBox.SetSizer(sizer4)
		for ctrl in playerOptions.GetChildren():
			sizer7.Add(ctrl, 1)
		playerOptions.SetSizer(sizer7)
		sizer.Add(sizer1, 1, wx.EXPAND)
		sizer.Add(sizer2, 1, wx.EXPAND)
		sizer.Add(preferencesBox, 1, wx.EXPAND)
		sizer.Add(downloadPreferencesBox, 1, wx.EXPAND)
		sizer.Add(playerOptions, 1, wx.EXPAND)
		sizer.Add(okCancelSizer, 1, wx.EXPAND)
		panel.SetSizer(sizer)
		changeButton.Bind(wx.EVT_BUTTON, self.onChange)
		self.autoDetectItem.Bind(wx.EVT_CHECKBOX, self.onCheck)
		self.autoLoadItem.Bind(wx.EVT_CHECKBOX, self.onCheck)
		self.autoCheckForUpdates.Bind(wx.EVT_CHECKBOX, self.onCheck)
		self.repeateTracks.Bind(wx.EVT_CHECKBOX, self.onCheck)
		self.autoPlayNext.Bind(wx.EVT_CHECKBOX, self.onCheck)
		self.continueWatching.Bind(wx.EVT_CHECKBOX, self.onCheck)
		okButton.Bind(wx.EVT_BUTTON, self.onOk)
		self.ShowModal()
	def onCheck(self, event):
		obj = event.EventObject
		if all((self.repeateTracks.Value, self.autoPlayNext.Value)) and obj in (self.repeateTracks, self.autoPlayNext):
			self.repeateTracks.Value = self.autoPlayNext.Value = False
		if obj.Name in self.preferences and config_get(obj.Name) == obj.Value:
			del self.preferences[obj.Name]
		elif not obj.Value == config_get(obj.Name):
			self.preferences[obj.Name] = obj.Value
	def onChange(self, event):
		new = wx.DirSelector(_("choose download folder"), os.path.join(os.getenv("userprofile"), "downloads"), parent=self)
		if not new == "":
			logger.info("Settings download path changed. path=%s", new)
			self.preferences['path'] = new
			self.pathField.Value = new
			self.pathField.SetFocus()
	def onOk(self, event):
		for key, item in self.preferences.items():
			logger.info("Saving setting. %s=%s", key, item)
			config_set(key, item)
		if not self.mp3Quality.Selection == int(config_get("conversion")):
			logger.info("Saving setting. conversion=%s", self.mp3Quality.Selection)
			config_set("conversion", self.mp3Quality.Selection)
		if not self.formats.Selection == int(config_get('defaultformat')):
			logger.info("Saving setting. defaultformat=%s", self.formats.Selection)
			config_set("defaultformat", self.formats.Selection)
		selected_cookie_browser = cookie_browser_values[self.cookiesBrowser.Selection]
		if not selected_cookie_browser == config_get("cookiesfrombrowser"):
			logger.info("Saving setting. cookiesfrombrowser=%s", selected_cookie_browser)
			config_set("cookiesfrombrowser", selected_cookie_browser)
		lang = {value:key for key, value in languages.items()}
		if not lang[self.languageBox.Selection] == config_get("lang"):
			logger.info("Saving setting. lang=%s", lang[self.languageBox.Selection])
			config_set("lang", lang[self.languageBox.Selection])
			msg = wx.MessageBox(_("you have changed program language to {}, which requires to restart the program to apply changes. would you like to do that now?").format(self.languageBox.StringSelection), _("alert"), style=wx.YES_NO, parent=self)
			os.execl(sys.executable, sys.executable, *sys.argv) if msg == 2 else None
		self.Destroy()
