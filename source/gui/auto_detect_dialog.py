import wx

from .playlist_dialog import PlaylistDialog
from .download_dialog import DownloadDialog

from media_player.media_gui import MediaGui
from utiles import get_video_stream, get_audio_stream



def link_type(url):
	cases = ("list", "channel", "playlist", "/user/")
	if cases[0] in url or cases[2] in url:
		return _("playlist")
	elif cases[1] in url or cases[3] in url:
		return _("channel")
	else:
		return _("Video")

class AutoDetectDialog(wx.Dialog):
	def __init__(self, parent, url):
		wx.Dialog.__init__(self, parent, title=parent.Title)
		self.url  = url
		self.Centre()
		panel = wx.Panel(self)
		msg = wx.StaticText(panel, -1, _("their is a link for YouTube {} detected in the clipboard. What would you like to do now?").format(link_type(url)))
		downloadButton = wx.Button(panel, -1, _("download"))
		playButton = wx.Button(panel, -1, _("play"))

		if link_type(self.url) == _("playlist"):
			playButton.Label = _("open...")
		elif link_type(url) != _("Video"):
			playButton.Disable() 
		cancelButton = wx.Button(panel, wx.ID_CANCEL, _("cancel"))
		downloadButton.Bind(wx.EVT_BUTTON, self.onDownload)
		playButton.Bind(wx.EVT_BUTTON, self.onPlay)
		self.ShowModal()
	def onDownload(self, event):
		dlg = DownloadDialog(wx.GetApp().GetTopWindow(), self.url)
		dlg.Show()
		self.Destroy()
	def onPlay(self, event):
		if link_type(self.url) == _("playlist"):
			PlaylistDialog(self.Parent, self.url)
			self.Destroy()
			return
		from .activity_dialog import LoadingDialog
		parent = self.Parent
		self.Destroy()
		stream = LoadingDialog(parent, _("playing"), get_audio_stream, self.url).res
		gui = MediaGui(parent, stream.title, stream, self.url)



