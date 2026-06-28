import os
import subprocess

import wx


class DownloadCompleteDialog(wx.Dialog):
	def __init__(self, parent, file_path=None, folder_path=None):
		super().__init__(parent, title=_("download complete"))
		self.file_path = file_path
		self.folder_path = folder_path or (os.path.dirname(file_path) if file_path else None)
		self.CentreOnParent()
		panel = wx.Panel(self)
		message = wx.StaticText(panel, -1, _("download has been completed successfully."))
		closeButton = wx.Button(panel, wx.ID_OK, _("&ok"))
		closeButton.SetDefault()
		buttons = []
		if self.file_path and os.path.exists(self.file_path):
			playButton = wx.Button(panel, -1, _("play downloaded file"))
			showButton = wx.Button(panel, -1, _("show downloaded file in file explorer"))
			playButton.Bind(wx.EVT_BUTTON, self.onPlay)
			showButton.Bind(wx.EVT_BUTTON, self.onShowFile)
			buttons.extend([playButton, showButton])
		elif self.folder_path and os.path.isdir(self.folder_path):
			openFolderButton = wx.Button(panel, -1, _("open download folder"))
			openFolderButton.Bind(wx.EVT_BUTTON, self.onOpenFolder)
			buttons.append(openFolderButton)
		buttons.append(closeButton)

		sizer = wx.BoxSizer(wx.VERTICAL)
		buttonSizer = wx.BoxSizer(wx.HORIZONTAL)
		sizer.Add(message, 0, wx.EXPAND)
		for button in buttons:
			buttonSizer.Add(button, 1, wx.EXPAND)
		sizer.Add(buttonSizer, 0, wx.EXPAND)
		panel.SetSizer(sizer)
		self.Fit()
		self.Bind(wx.EVT_CHAR_HOOK, self.onHook)

	def onPlay(self, event):
		os.startfile(self.file_path)
		self.EndModal(wx.ID_OK)

	def onShowFile(self, event):
		subprocess.Popen(["explorer", "/select,", self.file_path])
		self.EndModal(wx.ID_OK)

	def onOpenFolder(self, event):
		os.startfile(self.folder_path)
		self.EndModal(wx.ID_OK)

	def onHook(self, event):
		if event.KeyCode == wx.WXK_ESCAPE:
			self.EndModal(wx.ID_OK)
			return
		event.Skip()


def show_download_complete(parent, file_path=None, folder_path=None):
	dialog = DownloadCompleteDialog(parent, file_path=file_path, folder_path=folder_path)
	try:
		dialog.ShowModal()
	finally:
		dialog.Destroy()
