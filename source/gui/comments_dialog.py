import wx
from nvda_client.client import speak
from threading import Thread
from wx.lib.newevent import NewEvent
import pyperclip



LoadingComplete, EVT_LOADING_COMPLETE = NewEvent()



class CommentsDialog(wx.Dialog):
    def __init__(self, parent, comments):
        self.comments = comments
        super().__init__(parent, title=_("التعليقات"))

        self.CenterOnParent()
        self.SetSize(500, 500)
        p = wx.Panel(self)
        l1 = wx.StaticText(p, -1, _("التعليقات"))
        self.commentsBox = wx.ListBox(p, -1)
        closeButton = wx.Button(p, wx.ID_CLOSE, _("إغلاق"))
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(closeButton, 1)
        sizer1 = wx.BoxSizer(wx.HORIZONTAL)
        sizer1.Add(l1, 1)
        sizer1.Add(self.commentsBox, 1, wx.EXPAND)
        sizer.Add(sizer1)
        p.SetSizer(sizer)
        self.commentsBox.Bind(wx.EVT_LISTBOX, self.onNavigate)
        closeButton.Bind(wx.EVT_BUTTON, lambda e: self.Destroy())
        self.Bind(EVT_LOADING_COMPLETE, self.onComplete)
        self.Bind(wx.EVT_CLOSE, lambda e: self.Destroy())
        self.Bind(wx.EVT_CHAR_HOOK, self.onHook)
        self.contextSetup()
        hotkeys = wx.AcceleratorTable([
            (wx.ACCEL_CTRL, ord("L"), wx.ID_COPY),
        ])
        self.commentsBox.SetAcceleratorTable(hotkeys)
        self.count = 0
        self.displayComments()
        self.isLoading = False
        self.Show()
        try:
            self.commentsBox.Selection = 0
        except:
            pass
    def displayComments(self):
        for comment in self.comments.comments['result'][self.count:]:
            comment = [comment['content'], _("بواسطة {}").format(comment['author']['name'])]
            self.commentsBox.Append(". ".join(comment))
        self.count = self.commentsBox.Count

    def getComment(self, n):
        return self.comments.comments['result'][n]['content']
    def loadMore(self):
        if self.comments.hasMoreComments and not self.isLoading:
            try:
                self.isLoading = True
                comments = list(self.comments.comments['result'])
                self.comments.getNextComments()
                self.comments.comments['result'] = comments + self.comments.comments['result']
                wx.PostEvent(self, LoadingComplete())
            except Exception as e:
                speak(_("لم نتمكن من تحميل المزيد من التعليقات"))
            finally:
                self.isLoading = False
        elif self.isLoading:
            speak(_("لا يزال التحميل جار"))
        else:
            speak(_("ليس هناك المزيد من التعليقات"))

    def onNavigate(self, event):
        selection = self.commentsBox.Selection

        if selection == self.commentsBox.Count-1:
            Thread(target=self.loadMore).start()

    def onComplete(self, event):
        self.displayComments()
        speak(_("تم تحميل المزيد من التعليقات"))
    def contextSetup(self):
        contextMenu = wx.Menu()
        copyItem = contextMenu.Append(wx.ID_COPY, _("نسخ التعليق"))

        self.commentsBox.Bind(wx.EVT_CONTEXT_MENU, lambda e: self.commentsBox.PopupMenu(contextMenu) if self.commentsBox.Selection != -1 else None)
        self.commentsBox.Bind(wx.EVT_MENU, self.onCopy, id=wx.ID_COPY)
    def onCopy(self, event):
        selection = self.commentsBox.Selection
        if self.commentsBox.Selection != -1:
            pyperclip.copy(self.commentsBox.GetStringSelection())
            speak(_("تم نسخ التعليق المحدد إلى الحافظة"))
    def onHook(self, event):
        if event.KeyCode == wx.WXK_ESCAPE:
            self.Destroy()
        event.Skip()