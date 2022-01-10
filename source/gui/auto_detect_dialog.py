import wx
from .download_dialog import DownloadDialog
from media_player.media_gui import MediaGui
from utiles import get_video_stream



def link_type(url):
	cases = ("list", "channel", "playlist", "/user/")
	if cases[0] in url or cases[2] in url:
		return _("قائمة تشغيل")
	elif cases[1] in url or cases[3] in url:
		return _("قناة")
	else:
		return _("فيديو")

class AutoDetectDialog(wx.Dialog):
	def __init__(self, parent, url):
		wx.Dialog.__init__(self, parent, title=parent.Title)
		self.url  = url
		self.Centre()
		panel = wx.Panel(self)
		msg = wx.StaticText(panel, -1, _("لقد تم الكشف عن وجود رابط ل{} يوتيوب في الحافظة. يرجى اختيار الإجراء المطلوب").format(link_type(url)))
		downloadButton = wx.Button(panel, -1, _("تنزيل"))
		playButton = wx.Button(panel, -1, _("تشغيل"))
		if link_type(url) != _("فيديو"):
			playButton.Disable() 
		cancelButton = wx.Button(panel, wx.ID_CANCEL, _("إلغاء"))
		downloadButton.Bind(wx.EVT_BUTTON, self.onDownload)
		playButton.Bind(wx.EVT_BUTTON, self.onPlay)
		self.ShowModal()
	def onDownload(self, event):
		dlg = DownloadDialog(self.Parent, self.url)
		dlg.Show()
		self.Destroy()
	def onPlay(self, event):
		stream = get_video_stream(self.url)
		gui = MediaGui(self.Parent, stream.title, stream, self.url)
		self.Destroy()


