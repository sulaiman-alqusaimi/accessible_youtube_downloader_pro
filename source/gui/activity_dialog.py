import wx
from threading import Thread


class LoadingDialog(wx.Dialog):
    def __init__(self, parent, msg, function, *args, **kwargs):
        self.function = function
        self.args = args
        self.kwargs = kwargs
        super().__init__(parent)
        self.CenterOnParent()
        p = wx.Panel(self)
        self.message = wx.StaticText(p, -1, msg)
        self.message.SetCanFocus(True)
        self.message.SetFocus()
        indicator = wx.ActivityIndicator(p)
        indicator.Start()
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.message, 1, wx.EXPAND)
        sizer.AddStretchSpacer()
        sizer.Add(indicator, 1, wx.EXPAND)
        sizer.AddStretchSpacer()
        p.SetSizer(sizer)
        self.Bind(wx.EVT_CLOSE, lambda e: wx.Exit())
        self.Bind(wx.EVT_CHAR_HOOK, self.onHook)
        Thread(target=self.run).start()
        self.ShowModal()
    def run(self):
        try:
            self.res = self.function(*self.args, **self.kwargs)
            wx.CallAfter(self.Destroy)
        except Exception as e:
            wx.CallAfter(self.Destroy)
            raise e
    def onHook(self, event):
        if event.KeyCode in (wx.WXK_DOWN, wx.WXK_UP, wx.WXK_LEFT, wx.WXK_RIGHT):
            self.message.SetFocus()
            return
        event.Skip()
