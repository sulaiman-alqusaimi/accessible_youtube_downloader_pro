import wx


class DownloadProgress(wx.Frame):
	def __init__(self, parent, title=""):
		wx.Frame.__init__(self, parent=parent)
		self.Title = _("downloading - {}").format(title if title != "" else "accessible youtube downloader pro")
		self.Centre()
		panel = wx.Panel(self)
		self.textProgress = wx.Choice(panel, -1, choices=[_("download percentage: {}%").format(0), _("total file size: {} {}"), _("downloaded size: {} {}"), _("remaining file size: {} {}"), _("downloading speed: {} {}")])
		self.textProgress.Selection = 0
		self.gaugeProgress = wx.Gauge(panel, -1, range=100)
		self.Bind(wx.EVT_CLOSE, self.onClose)
	def onClose(self, event):
		message = wx.MessageBox(_("There is an active download. Do you want to cancel it?"), _("Exit"), style=wx.YES_NO, parent=self)
		if message == 2:
			self.Destroy()


