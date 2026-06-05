import requests
import wx
from wx.lib.newevent import NewEvent
import os
from paths import update_path
from threading import Thread
import shutil
import subprocess
import sys
from app_logger import get_logger


logger = get_logger()


ProgressChangedEvent, EVT_PROGRESS_CHANGED = NewEvent()
DownloadFinishedEvent, EVT_DOWNLOAD_FINISHED = NewEvent()

class UpdateDialog(wx.Dialog):
	def __init__(self, parent, url):
		super().__init__(None, title=_("download updates"))
		self.CentreOnParent()

		panel = wx.Panel(self)
		self.status = wx.TextCtrl(panel, -1, value=_("waiting for the download to start..."), style=wx.TE_READONLY|wx.TE_MULTILINE|wx.HSCROLL)
		cancelButton = wx.Button(panel, wx.ID_CANCEL, _("cancel the download"))
		self.progress = wx.Gauge(panel, -1, range=100)
		self.progress.Bind(EVT_PROGRESS_CHANGED, self.onChanged)
		self.Bind(EVT_DOWNLOAD_FINISHED, self.onFinished)
		cancelButton.Bind(wx.EVT_BUTTON, self.onCancel)
		self.Bind(wx.EVT_CLOSE, self.onClose)
		Thread(target=self.updateDownload, args=[url]).start()
		self.download = True
		self.ShowModal()

	def updateDownload(self, url):
		logger.info("Starting update download. url=%s", url)
		if os.path.exists(update_path):
			shutil.rmtree(update_path)
		os.mkdir(update_path)
		name = os.path.join(update_path, url.split("/")[-1])
		try:
			with requests.get(url, stream=True) as r:
				if r.status_code != 200:
					logger.error("Update download failed. status=%s url=%s", r.status_code, url)
					self.errorAction()
					return
				size = r.headers.get("content-length")
				try:
					size = int(size)
				except TypeError:
					logger.error("Update download missing content length. url=%s", url)
					self.errorAction()
					return
				recieved = 0
				progress = 0
				with open(name, "wb") as file:
					for part in r.iter_content(1024):
						file.write(part)
						if not self.download:
							logger.info("Update download cancelled. url=%s", url)
							file.close()
							shutil.rmtree(update_path)
							self.Destroy()
							return

						recieved += len(part)
						progress = int(
							(recieved/size)*100
						)
						wx.PostEvent(self.progress, ProgressChangedEvent(value=progress))
			wx.PostEvent(self, DownloadFinishedEvent(path=name))
		except requests.ConnectionError:
			logger.exception("Update download connection error. url=%s", url)
			self.errorAction()

	def errorAction(self):
		logger.error("Update error action triggered")
		wx.MessageBox(_("unable to update the application right now "), _("error"), style=wx.ICON_ERROR, parent=self)
		shutil.rmtree(update_path)
		self.Destroy()
	def onChanged(self, event):
		self.progress.SetValue(event.value)
		self.status.SetValue(_("downloading the update {}%").format(event.value))

	def onFinished(self, event):
		logger.info("Update download finished. path=%s", event.path)
		wx.MessageBox(_("the application update has been downloaded successfully. please click on ok to proceed to the installation process."), _("success"), parent=self)
		try:
			self.status.Value = _("installing the update")
			path = os.path.join(update_path, event.path)
			subprocess.Popen('"{}" /silent'.format(path), shell=True)
		except Exception:
			logger.exception("Could not start update installer. path=%s", event.path)
			wx.MessageBox(_("an unknown error occurred while trying to launch the update file. Try to update the application again, or contact the developer to report the issue."), _("error"), style=wx.ICON_ERROR, parent=self)
			self.Destroy()
			return
		sys.exit()
	def onCancel(self, event):
		logger.info("Update download cancellation requested")
		self.download = False
	def onClose(self, event):
		if self.download:
			message = wx.MessageBox(_("There is an active download. Do you want to cancel it?"), _("Exit"), style=wx.YES_NO, parent=self)
			if message == wx.YES:
				self.download = False
			return
		self.Destroy()
