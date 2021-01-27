import wx
from language_handler import init_translation


try:
	init_translation("accessible_youtube_downloader")
except:
	_ = lambda msg: msg


class DownloadProgress(wx.Frame):
	def __init__(self, parent, title=""):
		wx.Frame.__init__(self, parent=parent)
		self.Title = _("جاري التنزيل - {}").format(title if title != "" else "accessible youtube downloader pro")
		self.Centre()
		panel = wx.Panel(self)
		self.textProgress = wx.Choice(panel, -1, choices=[_("نسبة التنزيل: {}%").format(0), _("حجم الملف الإجمالي: {} {}"), _("مقدار الحجم الذي تم تنزيله: {} {}"), _("المقدار المتبقي: {} {}"), _("سرعة التنزيل: {} {}")])
		self.textProgress.Selection = 0
		self.gaugeProgress = wx.Gauge(panel, -1, range=100)
		self.Bind(wx.EVT_CLOSE, self.onClose)
	def onClose(self, event):
		message = wx.MessageBox("هناك عملية تنزيل جارية. هل تريد إلغاءها؟", "إنهاء", style=wx.YES_NO, parent=self)
		if message == 2:
			self.Destroy()


