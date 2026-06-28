import wx


class DownloadProgress(wx.Frame):
	def __init__(self, parent, title=""):
		wx.Frame.__init__(self, parent=parent)
		self.Title = _("downloading - {}").format(title if title != "" else "accessible youtube downloader pro")
		self.Centre()
		self.downloader = None
		self.completed_file = None
		self.cancelled = False
		panel = wx.Panel(self)
		self.textProgress = wx.Choice(panel, -1, choices=[_("download percentage: {}%").format(0), _("total file size: {} {}"), _("downloaded size: {} {}"), _("remaining file size: {} {}"), _("downloading speed: {} {}")])
		self.textProgress.Selection = 0
		self.gaugeProgress = wx.Gauge(panel, -1, range=100)
		self.stopButton = wx.Button(panel, -1, _("stop download"))
		sizer = wx.BoxSizer(wx.VERTICAL)
		sizer.Add(self.textProgress, 1, wx.EXPAND)
		sizer.Add(self.gaugeProgress, 1, wx.EXPAND)
		sizer.Add(self.stopButton, 1, wx.EXPAND)
		panel.SetSizer(sizer)
		self.stopButton.Bind(wx.EVT_BUTTON, self.onStop)
		self.Bind(wx.EVT_CLOSE, self.onClose)
		self.Bind(wx.EVT_CHAR_HOOK, self.onHook)

	def set_downloader(self, downloader):
		self.downloader = downloader

	def set_completed_file(self, path):
		self.completed_file = path
		self.stopButton.Disable()

	def set_cancelled(self):
		self.cancelled = True
		self.stopButton.Disable()
		if not self.IsShown():
			self.Destroy()
			return
		self.textProgress.SetString(0, _("download stopped"))
		self.textProgress.Selection = 0

	def onStop(self, event):
		self.stop_download()

	def stop_download(self):
		self.cancelled = True
		if self.downloader is not None:
			self.downloader.cancel()
		self.stopButton.Disable()
		self.Hide()

	def onClose(self, event):
		if self.downloader is not None and not self.cancelled and self.stopButton.Enabled:
			message = wx.MessageBox(_("There is an active download. Do you want to cancel it?"), _("Exit"), style=wx.YES_NO, parent=self)
			if message != wx.YES:
				return
			self.stop_download()
			return
		self.Destroy()

	def onHook(self, event):
		if event.KeyCode == wx.WXK_ESCAPE:
			if self.downloader is not None and not self.cancelled and self.stopButton.Enabled:
				self.stop_download()
			else:
				self.Destroy()
			return
		event.Skip()


