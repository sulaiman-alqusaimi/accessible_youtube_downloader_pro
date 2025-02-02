import wx



class SearchDialog(wx.Dialog):
	def __init__(self, parent, value=""):
		wx.Dialog.__init__(self, parent=parent, title=_("بحث"))
		self.Centre()
		panel = wx.Panel(self)
		sizer = wx.BoxSizer(wx.VERTICAL)
		lbl = wx.StaticText(panel, -1, _("ابحث في youtube: "))
		self.searchField = wx.TextCtrl(panel, -1, value=value)
		lbl1 = wx.StaticText(panel, -1, _("فلتر: "))
		self.filterBox = wx.Choice(panel, -1, choices=
							 [_("بلا فلتر"), 
		 _("بث مباشر"), 
		 _("تاريخ الرفع"), 
		 _("عدد المشاهدات"), 
		#  _("قائمة تشغيل")
		 ])
		self.filterBox.Selection = 0
		searchButton = wx.Button(panel, wx.ID_OK, _("ابحث"))
		searchButton.SetDefault()
		searchButton.Enabled = False if value == "" else True
		closeButton = wx.Button(panel, wx.ID_CANCEL, _("إغلاق"))
		sizer1 = wx.BoxSizer(wx.HORIZONTAL)
		sizer1.Add(lbl, 1)
		sizer1.Add(self.searchField, 1)
		sizer2 = wx.BoxSizer(wx.HORIZONTAL)
		sizer2.Add(lbl1, 1)
		sizer2.Add(self.filterBox, 1)
		sizer3 = wx.BoxSizer(wx.HORIZONTAL)
		sizer3.Add(searchButton, 1)
		sizer3.Add(closeButton, 1)
		sizer.Add(sizer1, 1, wx.EXPAND)
		sizer.Add(sizer2, 1, wx.EXPAND)
		sizer.Add(sizer3, 1, wx.EXPAND)
		panel.SetSizer(sizer)
		self.searchField.Bind(wx.EVT_TEXT, lambda event: searchButton.Disable() if self.searchField.Value == "" else searchButton.Enable())
		searchButton.Bind(wx.EVT_BUTTON, self.onSearch)
		closeButton.Bind(wx.EVT_BUTTON, self.onClose)
		self.ShowModal()
	def onSearch(self, event):
		self.query = self.searchField.Value if self.searchField.Value != "" else None
		self.filter = self.filterBox.Selection
		self.Destroy()
	def onClose(self, event):
		self.query = None
		self.filter = None
		self.Destroy()