import wx


class CustomLabel(wx.StaticText):
	# a customed focussable wx.StaticText 
	def __init__(self, *args, **kwargs):
		wx.StaticText.__init__(self, *args, **kwargs)
	def AcceptsFocusFromKeyboard(self):
		# overwriting the AcceptsFocusFromKeyboard to return True
		return True


class CustomButton(wx.Button):
	def __init__(self, *args, **kwargs):
		wx.Button.__init__(self, *args, **kwargs)
	def AcceptsFocusFromKeyboard(self):
		return False
