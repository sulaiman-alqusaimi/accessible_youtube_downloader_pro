import wx
from language_handler import init_translation

try:
	init_translation("accessible_youtube_downloader")
except:
	_ = lambda msg: msg


class LinkDlg(wx.Dialog):
	def __init__(self, parent):
		wx.Dialog.__init__(self, parent=parent, title=_("ادخل رابط الفيديو لتشغيله من خلال مشغل البرنامج"))
		self.Centre()
		panel = wx.Panel(self)
		sizer = wx.BoxSizer(wx.VERTICAL)
		lbl = wx.StaticText(panel, -1, _("رابط المقطع"))
		self.link = wx.TextCtrl(panel, -1, value="")
		self.mode = wx.RadioBox(panel, -1, _("التشغيل ك: "), choices=[_("مقطع فيديو"), _("مقطع صوتي")])
		okButton = wx.Button(panel, wx.ID_OK, _("موافق"))
		okButton.SetDefault()
		sizer1 = wx.BoxSizer(wx.HORIZONTAL)
		sizer1.Add(lbl, 1)
		sizer1.Add(self.link, 1)
		sizer.Add(sizer1, 1, wx.EXPAND)
		sizer.Add(self.mode, 1, wx.ALL)
		sizer.Add(okButton, 1)
		panel.SetSizer(sizer)
		okButton.Bind(wx.EVT_BUTTON, self.onOk)
		self.ShowModal()
	def onOk(self, event):
		link = self.link.Value
		audio = True if self.mode.Selection == 1 else False
		self.data = {"link": link, "audio": audio}
		self.Destroy()
