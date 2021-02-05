import wx





class Viewer(wx.Dialog):
	def __init__(self, parent, title, content):
		wx.Dialog.__init__(self, parent, title=title)
		self.Centre()
		self.Maximize(True)
		sizer= wx.BoxSizer(wx.VERTICAL)
		panel = wx.Panel(self)
		textBox = wx.TextCtrl(panel,-1, value=content, style=wx.TE_READONLY|wx.TE_MULTILINE|wx.HSCROLL|wx.TE_CENTRE)
		closeButton = wx.Button(panel,-1, _("إغلاق"))
		closeButton.Bind(wx.EVT_BUTTON, lambda event: self.Destroy())
		sizer.Add(closeButton,0)
		sizer.Add(textBox, 1, wx.EXPAND)
		panel.SetSizer(sizer)
		self.Bind(wx.EVT_CHAR_HOOK, self.onEscape)
	def onEscape(self, event):
		if event.GetKeyCode() == wx.WXK_ESCAPE:
			self.Destroy()
		event.Skip()


