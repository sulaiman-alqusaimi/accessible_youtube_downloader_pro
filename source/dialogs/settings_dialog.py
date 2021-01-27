import os
import sys

import wx
from language_handler import init_translation
from settings_handler import config_get, config_set

try:
	init_translation("accessible_youtube_downloader")
except:
	_ = lambda msg: msg

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
		okButton = wx.Button(panel, wx.ID_OK, _("مواف&ق"), name="ok_cancel")
		okButton.SetDefault()
		cancelButton = wx.Button(panel, wx.ID_CANCEL, _("إل&غاء"), name="ok_cancel")
		sizer = wx.BoxSizer(wx.VERTICAL)
		sizer1 = wx.BoxSizer(wx.HORIZONTAL)
		sizer2 = wx.BoxSizer(wx.HORIZONTAL)
		sizer3 = wx.BoxSizer(wx.HORIZONTAL)
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
		sizer.Add(sizer1, 1, wx.EXPAND)
		sizer.Add(sizer2, 1, wx.EXPAND)
		sizer.Add(preferencesBox, 1, wx.EXPAND)
		sizer.Add(okCancelSizer, 1, wx.EXPAND)
		panel.SetSizer(sizer)
		changeButton.Bind(wx.EVT_BUTTON, self.onChange)
		self.autoDetectItem.Bind(wx.EVT_CHECKBOX, self.onCheck)
		self.autoLoadItem.Bind(wx.EVT_CHECKBOX, self.onCheck)
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
		if not new == "" and not new == config_get("path"):
			self.path = new
			self.pathField.Value = self.path
	def onOk(self, event):
		try:
			for key, item in self.preferences.items():
				config_set(key, item)
			config_set("path", self.path)
		except AttributeError:
			pass
		for key, item in self.preferences.items():
			config_set(key, item)

		lang = {value:key for key, value in languages.items()}
		if not lang[self.languageBox.Selection] == config_get("lang"):
			config_set("lang", lang[self.languageBox.Selection])
			msg = wx.MessageBox(_("لقد قمت بتغيير لغة البرنامج إلى {}, مما يعني أنه ينبغي عليك إعادة تشغيل البرنامج لتطبيق التعديلات. هل تريد القيام بذلك حالًا?").format(self.languageBox.StringSelection), _("تنبيه"), style=wx.YES_NO, parent=self)
			os.execl(sys.executable, sys.executable, *sys.argv) if msg == 2 else None
		self.Destroy()
