import os
import sys

import wx
from settings_handler import config_get, config_set



languages = {"ar": 0, "en": 1}

class SettingsDialog(wx.Dialog):
	def __init__(self, parent):
		wx.Dialog.__init__(self, parent, title=_("الإعدادات"))
		self.SetSize(500, 500)
		self.Centre()
		self.preferences = {}
		panel = wx.Panel(self)
		lbl = wx.StaticText(panel, -1, _("لغة البرنامج: "), name="language")
		self.languageBox = wx.Choice(panel, -1, name="language")
		self.languageBox.Set(("العربية", "English"))
		try:
			self.languageBox.Selection = languages[config_get("lang")]
		except KeyError:
			self.languageBox.Selection = 0
		lbl1 = wx.StaticText(panel, -1, _("مسار مجلد التنزيل: "), name="path")
		self.pathField = wx.TextCtrl(panel, -1, value=config_get("path"), name="path", style=wx.TE_READONLY|wx.TE_MULTILINE|wx.HSCROLL)
		changeButton = wx.Button(panel, -1, _("&تغيير المسار"), name="path")
		preferencesBox = wx.StaticBox(panel, -1, _("التفضيلات العامة"))
		self.autoDetectItem = wx.CheckBox(preferencesBox, -1, _("اكتشاف الروابط تلقائيًا عند فتح البرنامج"), name="autodetect")
		self.autoLoadItem = wx.CheckBox(preferencesBox, -1, _("تحميل المزيد من نتائج البحث عند الوصول إلى نهاية قائمة الفيديوهات المعروضة"), name="autoload")
		self.autoDetectItem.SetValue(config_get("autodetect"))
		self.autoLoadItem.SetValue(config_get("autoload"))
		downloadPreferencesBox = wx.StaticBox(panel, -1, _("إعدادات التنزيل"))
		lbl2 = wx.StaticText(downloadPreferencesBox, -1, _("صيغة التحميل المباشر: "))
		self.formats = wx.Choice(downloadPreferencesBox, -1, choices=[_("فيديو (mp4)"), _("صوت (m4a)"), _("صوت (mp3)")])
		self.formats.Selection = int(config_get('defaultformat'))
		lbl3 = wx.StaticText(downloadPreferencesBox, -1, _("جودة تحويل ملفات mp3: "))
		self.mp3Quality = wx.Choice(downloadPreferencesBox, -1, choices=["96 kbps", "128 kbps", "192 kbps"], name="conversion")
		self.mp3Quality.Selection = int(config_get("conversion"))
		playerOptions = wx.StaticBox(panel, -1, _("إعدادات المشغل"))
		self.repeateTracks = wx.CheckBox(playerOptions, -1, _("إعادة تشغيل المقطع تلقائيًا عند انتهائه"), name="repeatetracks")
		self.repeateTracks.Value = config_get("repeatetracks")
		okButton = wx.Button(panel, wx.ID_OK, _("مواف&ق"), name="ok_cancel")
		okButton.SetDefault()
		cancelButton = wx.Button(panel, wx.ID_CANCEL, _("إل&غاء"), name="ok_cancel")
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
		sizer4.Add(sizer5)
		sizer4.Add(sizer6)
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
		self.repeateTracks.Bind(wx.EVT_CHECKBOX, self.onCheck)
		okButton.Bind(wx.EVT_BUTTON, self.onOk)
		self.ShowModal()
	def onCheck(self, event):
		self.preferences = {}
		obj = event.EventObject
		if obj.Name in self.preferences and config_get(obj.Name) == obj.Value:
			del self.preferences[obj.Name]
		elif not obj.Value == config_get(obj.Name):
			self.preferences[obj.Name] = obj.Value
		if self.preferences == {}:
			del self.preferences
	def onChange(self, event):
		new = wx.DirSelector(_("اختر مجلد التنزيل"), os.path.join(os.getenv("userprofile"), "downloads"), parent=self)
		if not new == "":
			self.preferences['path'] = new
			self.pathField.Value = new
			self.pathField.SetFocus()
	def onOk(self, event):
		try:
			for key, item in self.preferences.items():
				config_set(key, item)
		except AttributeError:
			pass
		if not self.mp3Quality.Selection == int(config_get("conversion")):
			config_set("conversion", self.mp3Quality.Selection)
		config_set("defaultformat", self.formats.Selection) if not self.formats.Selection == int(config_get('defaultformat')) else None
		lang = {value:key for key, value in languages.items()}
		if not lang[self.languageBox.Selection] == config_get("lang"):
			config_set("lang", lang[self.languageBox.Selection])
			msg = wx.MessageBox(_("لقد قمت بتغيير لغة البرنامج إلى {}, مما يعني أنه ينبغي عليك إعادة تشغيل البرنامج لتطبيق التعديلات. هل تريد القيام بذلك حالًا?").format(self.languageBox.StringSelection), _("تنبيه"), style=wx.YES_NO, parent=self)
			os.execl(sys.executable, sys.executable, *sys.argv) if msg == 2 else None
		self.Destroy()
