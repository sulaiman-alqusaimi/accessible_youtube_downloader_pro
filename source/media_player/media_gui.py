import webbrowser
import pyperclip
import wx
from gui.download_progress import DownloadProgress
from download_handler.downloader import downloadAction
from nvda_client.client import speak
from settings_handler import config_get, config_set
import application
from utiles import direct_download, extract_youtube_comments, get_audio_stream, get_video_stream
from vlc import State, Media
from gui.settings_dialog import SettingsDialog
from gui.description import DescriptionDialog
from gui.custom_controls import CustomButton
from gui.comments_dialog import CommentsDialog
from youtubesearchpython import Video
from threading import Thread
from database import Continue, ViewHistory
from media_player.player import Player
from app_logger import get_logger


logger = get_logger()


class AudioOutputDeviceDialog(wx.Dialog):
	def __init__(self, parent, devices, selected_device):
		wx.Dialog.__init__(self, parent, title=_("audio output device"))
		self.SetSize(450, 200)
		self.Centre()
		self.devices = [{"id": "", "description": _("default audio output device")}] + devices
		panel = wx.Panel(self)
		label = wx.StaticText(panel, -1, _("audio output device: "))
		self.deviceBox = wx.Choice(panel, -1, choices=[device["description"] for device in self.devices])
		self.deviceBox.Selection = self.get_selection_for_device(selected_device)
		okButton = wx.Button(panel, wx.ID_OK, _("&ok"))
		okButton.SetDefault()
		cancelButton = wx.Button(panel, wx.ID_CANCEL, _("&cancel"))
		deviceSizer = wx.BoxSizer(wx.HORIZONTAL)
		buttonSizer = wx.BoxSizer(wx.HORIZONTAL)
		sizer = wx.BoxSizer(wx.VERTICAL)
		deviceSizer.Add(label, 1)
		deviceSizer.Add(self.deviceBox, 2, wx.EXPAND)
		buttonSizer.Add(okButton, 1)
		buttonSizer.Add(cancelButton, 1)
		sizer.Add(deviceSizer, 1, wx.EXPAND)
		sizer.Add(buttonSizer, 1, wx.EXPAND)
		panel.SetSizer(sizer)

	def get_selection_for_device(self, selected_device):
		for index, device in enumerate(self.devices):
			if device["id"] == selected_device:
				return index
		return 0

	def get_selected_device(self):
		return self.devices[self.deviceBox.Selection]



def has_player(method):
	def rapper(self, *args):
		if self.player is not None:
			method(self, *args)
	return rapper


class MediaGui(wx.Frame):

	def __init__(self, parent, title, stream, url, can_download=True, results=None, audio_mode=False, history_data=None):

		logger.info("Opening media window. title=%s audio_mode=%s can_download=%s url=%s", title, audio_mode, can_download, url)
		wx.Frame.__init__(self, parent, title=f'{title} - {application.name}')
		self.title = title
		self.stream = not can_download
		self.seek = int(config_get("seek"))
		self.results = results
		self.audio_mode = audio_mode
		self.path = config_get('path')
		self.Centre()
		self.SetSize(wx.DisplaySize())
		self.Maximize(True)
		self.SetBackgroundColour(wx.BLACK)
		self.player = None
		self.url = url
		self.current_index = self.get_current_result_index()
		previousButton = CustomButton(self, -1, _("previous"), name="controls")
		previousButton.Show() if self.results is not None else previousButton.Hide()
		beginingButton = CustomButton(self, -1, _("restart from beginning"), name="controls")
		rewindButton = CustomButton(self, -1, _("rewind<"), name="controls")
		playButton = CustomButton(self, -1, _("play/pause"), name="controls")
		forwardButton = CustomButton(self, -1, _("forward>"), name="controls")
		nextButton = CustomButton(self, -1, _("next"), name="controls")
		nextButton.Show() if self.results is not None else nextButton.Hide()
		sizer = wx.BoxSizer(wx.VERTICAL)
		sizer1 = wx.BoxSizer(wx.HORIZONTAL)
		for control in self.GetChildren():
			if control.Name == "controls":
				sizer1.Add(control, 1)
		sizer.AddStretchSpacer()
		sizer.Add(sizer1)
		self.SetSizer(sizer)
		menuBar = wx.MenuBar()
		trackOptions = wx.Menu()
		downloadMenu = wx.Menu()
		videoItem = downloadMenu.Append(-1, _("Video"))
		audioMenu = wx.Menu()
		m4aItem = audioMenu.Append(-1, "m4a")
		mp3Item = audioMenu.Append(-1, "mp3")
		downloadMenu.AppendSubMenu(audioMenu, _("audio"))
		downloadId = trackOptions.AppendSubMenu(downloadMenu, _("download")).GetId()
		trackOptions.Enable(downloadId, can_download)
		directDownloadItem = trackOptions.Append(-1, _("direct download...\tctrl+d"))
		directDownloadItem.Enable(can_download)
		descriptionItem = trackOptions.Append(-1, _("video description\tctrl+shift+d"))
		commentsItem = trackOptions.Append(-1, _("comments...\tctrl+shift+j"))
		commentsItem.Enable(can_download)
		copyItem = trackOptions.Append(-1, _("copy video link\tctrl+l"))
		browserItem = trackOptions.Append(-1, _("open in browser\tctrl+b"))
		audioOutputDeviceItem = trackOptions.Append(-1, _("audio output device...\tf12"))
		settingsItem = trackOptions.Append(-1, _("settings...\talt+s"))
		hotKeys = wx.AcceleratorTable([
			(wx.ACCEL_CTRL, ord("D"), directDownloadItem.GetId()),
			(wx.ACCEL_CTRL|wx.ACCEL_SHIFT, ord("D"), descriptionItem.GetId()),
			(wx.ACCEL_CTRL, ord("L"), copyItem.GetId()),
			(wx.ACCEL_CTRL, ord("B"), browserItem.GetId()),
			(wx.ACCEL_NORMAL, wx.WXK_F12, audioOutputDeviceItem.GetId()),
			(wx.ACCEL_ALT, ord("S"), settingsItem.GetId()),
			(wx.ACCEL_CTRL + wx.ACCEL_SHIFT, ord("J"), commentsItem.GetId())
])
		self.SetAcceleratorTable(hotKeys)
		menuBar.Append(trackOptions, _("video options"))
		self.SetMenuBar(menuBar)
		self.Bind(wx.EVT_MENU, self.onVideoDownload, videoItem)
		self.Bind(wx.EVT_MENU, self.onM4aDownload, m4aItem)
		self.Bind(wx.EVT_MENU, self.onMp3Download, mp3Item)
		self.Bind(wx.EVT_MENU, self.onDirect, directDownloadItem)
		self.Bind(wx.EVT_MENU, self.onDescription, descriptionItem)
		self.Bind(wx.EVT_MENU, self.onComments, commentsItem)
		self.Bind(wx.EVT_MENU, self.onCopy, copyItem)
		self.Bind(wx.EVT_MENU, self.onBrowser, browserItem)
		self.Bind(wx.EVT_MENU, self.onAudioOutputDevice, audioOutputDeviceItem)
		self.Bind(wx.EVT_MENU, lambda event: SettingsDialog(self), settingsItem)
		self.Bind(wx.EVT_KEY_DOWN, self.onKeyDown)
		self.prev_id = 100
		self.play_pause_id = 150
		self.next_id = 200
		self.registerHotKey()
		for hot_id in [self.prev_id, self.play_pause_id, self.next_id]:
			self.Bind(wx.EVT_HOTKEY, self.onHot, id=hot_id)
		for control in self.GetChildren():
			control.Bind(wx.EVT_KEY_DOWN, self.onKeyDown)
		previousButton.Bind(wx.EVT_BUTTON, lambda event: self.previous())
		beginingButton.Bind(wx.EVT_BUTTON, lambda event: self.beginingAction())
		rewindButton.Bind(wx.EVT_BUTTON, lambda event: self.rewindAction())
		playButton.Bind(wx.EVT_BUTTON, lambda event: self.playAction())
		forwardButton.Bind(wx.EVT_BUTTON, lambda event: self.forwardAction())
		nextButton.Bind(wx.EVT_BUTTON, lambda event: self.next())
		self.Bind(wx.EVT_CLOSE, lambda event: self.closeAction())
		self.Show()
		self.player = Player(stream.url, self.GetHandle(), self)
		self.record_history(history_data or self.history_data_from_stream(stream, title, url))
		if self.url in Continue.get_all() and config_get("continue"):
			self.player.media.set_position(Continue.get_all()[url])
		Thread(target=self.extract_description).start()
		Thread(target=self.extract_comments).start()

	def history_data_from_stream(self, stream, title, url):
		return {
			"title": getattr(stream, "title", None) or title,
			"url": getattr(stream, "webpage_url", None) or url,
			"views": getattr(stream, "view_count", None),
			"upload_date": getattr(stream, "upload_date", ""),
			"channel_name": getattr(stream, "channel_name", ""),
			"channel_url": getattr(stream, "channel_url", ""),
		}

	def get_history_data_for_index(self, index, title, url):
		if self.results is None:
			return {"title": title, "url": url}
		if hasattr(self.results, "get_history_data"):
			return self.results.get_history_data(index)
		if isinstance(self.results, list):
			data = self.results[index].copy()
			data.setdefault("title", title)
			data.setdefault("url", url)
			return data
		return {"title": title, "url": url}

	def record_history(self, data):
		if not data or not data.get("url"):
			return
		try:
			logger.info("Adding video to view history. title=%s url=%s", data.get("title"), data.get("url"))
			ViewHistory().add(data)
		except Exception:
			logger.exception("Could not add video to view history. url=%s", data.get("url"))


	def playAction(self):
		state = self.player.media.get_state()
		if state in (State.NothingSpecial, State.Stopped):
			self.player.media.play()
		elif state in (State.Playing, State.Paused):
			if not self.stream:
				self.player.media.pause()
			else: 
				self.player.media.stop()

	@has_player
	def forwardAction(self):
		self.player.seek_seconds(self.seek)

	@has_player
	def rewindAction(self):
		self.player.seek_seconds(-self.seek)

	def set_position(self, key):
		step = int(chr(key))/10
		self.player.media.set_position(step)
		speak(_("elapsed time: {}").format(self.player.get_elapsed()))

	@has_player
	def beginingAction(self):
		self.player.media.set_position(0.0)
		speak(_("restart from beginning"))
		if self.player.media.get_state() in (State.NothingSpecial, State.Stopped):
			self.player.media.play()

	def closeAction(self):
		if self.player is not None:
			logger.info("Closing media window. url=%s position=%s", self.url, self.player.media.get_position())
			if self.player.media.get_position() in (0.0, -1) and self.url in Continue.get_all():
				Continue.remove_continue(self.url)
			elif self.url in Continue.get_all():
				Continue.update(self.url, self.player.media.get_position())
			else:
				Continue.new_continue(self.url, self.player.media.get_position())
			self.player.media.stop()
		self.GetParent().Show()

		self.Destroy()
	def registerHotKey(self):
		self.RegisterHotKey(
			self.prev_id,
			0, wx.WXK_MEDIA_PREV_TRACK)
		self.RegisterHotKey(
			self.play_pause_id,
			0, wx.WXK_MEDIA_PLAY_PAUSE)
		self.RegisterHotKey(
			self.next_id,
			0, wx.WXK_MEDIA_NEXT_TRACK)
	def onHot(self, event):
		if event.Id == self.prev_id:
			self.previous()
		elif event.Id == self.play_pause_id:
			self.playAction()
		elif event.Id == self.next_id:
			self.next()

	def onKeyDown(self, event):
		if event.GetKeyCode() in (wx.WXK_SPACE, wx.WXK_PAUSE):
			self.playAction()
		elif event.GetKeyCode() == wx.WXK_RIGHT and not event.HasAnyModifiers():
			self.forwardAction()
		elif event.GetKeyCode() == wx.WXK_LEFT and not event.HasAnyModifiers():
			self.rewindAction()
		elif event.controlDown and event.KeyCode == wx.WXK_RIGHT:
			self.next()
		elif event.controlDown and event.KeyCode == wx.WXK_LEFT:
			self.previous()
		elif event.GetKeyCode() == wx.WXK_UP:
			self.increase_volume()
		elif event.GetKeyCode() == wx.WXK_DOWN:
			self.decrease_volume()
		elif event.GetKeyCode() == wx.WXK_HOME:
			self.beginingAction()
		elif event.GetKeyCode() == wx.WXK_F12:
			self.onAudioOutputDevice(event)
		elif event.KeyCode in range(49, 58):
			self.set_position(event.KeyCode)
		elif event.controlDown and event.shiftDown and event.KeyCode == ord("L"):
			self.get_duration()
		elif event.controlDown and event.shiftDown and event.KeyCode == ord("T"):
			if self.player is not None:
				speak(_("elapsed time: {}").format(self.player.get_elapsed()))
		elif event.KeyCode == ord("S"):

			if self.player is not None:
				self.player.media.set_rate(1.4)
				speak(_("fast"))

		elif event.KeyCode == ord("D"):

			if self.player is not None:

				self.player.media.set_rate(1.0)

				speak(_("normal"))

		elif event.KeyCode == ord("F"):

			if self.player is not None:

				self.player.media.set_rate(0.6)

				speak(_("slow"))

		elif event.GetKeyCode() in (ord("-"), wx.WXK_NUMPAD_SUBTRACT):

			self.seek -= 1

			if self.seek < 1:

				self.seek = 1

			speak("{} {} {}".format(_("track moving accuracy: "), self.seek, _("second/s")))

			config_set("seek", self.seek)

		elif event.GetKeyCode() in (ord("="), wx.WXK_NUMPAD_ADD):

			self.seek += 1

			if self.seek > 10:

				self.seek = 10

			speak("{} {} {}".format(_("track moving accuracy: "), self.seek, _("second/s")))

			config_set("seek", self.seek)

		elif event.KeyCode == ord("R"):

			if config_get("repeatetracks"):

				config_set("repeatetracks", False)

				speak(_("repeate off"))
			else:

				config_set("repeatetracks", True)

				speak(_("repeate on"))
				config_set("autonext", False)
		elif event.KeyCode == ord("N"):

			if config_get("autonext"):

				config_set("autonext", False)

				speak(_("auto play the next track off"))
			else:

				config_set("autonext", True)

				speak(_("auto play the next track on"))
				config_set("repeatetracks", False)

		elif event.KeyCode in (wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER):

			self.togleFullScreen()

		elif event.KeyCode == wx.WXK_ALT:

			if self.IsFullScreen():

				self.ShowFullScreen(False)
			else:
				event.Skip()

		elif event.GetKeyCode() == wx.WXK_ESCAPE:

			self.closeAction()
		else:
			event.Skip()

	@has_player
	def get_duration(self):
			speak(_("duration: {}").format(self.player.get_duration()))

	@has_player
	def increase_volume(self):
		self.player.volume = self.player.volume+5 if self.player.volume < 350 else 350
		self.player.media.audio_set_volume(self.player.volume)
		speak(f"{self.player.volume}%")
		config_set("volume", self.player.volume)
	@has_player
	def decrease_volume(self):
		self.player.volume = self.player.volume-5 if self.player.volume > 0 else 0
		self.player.media.audio_set_volume(self.player.volume)
		speak(f"{self.player.volume}%")
		config_set("volume", self.player.volume)

	def togleFullScreen(self):
		self.ShowFullScreen(not self.IsFullScreen())
		if self.IsFullScreen():
			speak(_("full screen mode enabled"))
		else:
			speak(_("full screen mode disabled"))

	def get_current_result_index(self):
		if self.results is None:
			return None
		for control_name in ("searchResults", "videosBox", "favList", "historyList"):
			control = getattr(self.Parent, control_name, None)
			if control is not None and control.Selection != wx.NOT_FOUND:
				return control.Selection
		return 0

	def get_result_count(self):
		if self.results is None:
			return 0
		if isinstance(self.results, list):
			return len(self.results)
		if hasattr(self.results, "results"):
			return len(self.results.results)
		if hasattr(self.results, "videos"):
			return len(self.results.videos)
		return self.results.count

	def maybe_load_more_results(self, index):
		if isinstance(self.results, list):
			return
		count = self.get_result_count()
		if count == 0 or index < count-2:
			return

		def load_more():
			if hasattr(self.Parent, 'searchResults'):
				if self.results.load_more():
					wx.CallAfter(self.Parent.searchResults.Append, self.results.get_last_titles())
			elif hasattr(self.Parent, 'videosBox'):
				if self.results.next():
					wx.CallAfter(self.Parent.videosBox.Append, self.results.get_new_titles())

		Thread(target=load_more).start()

	def changeTrack(self, index):
		logger.info("Changing track. index=%s", index)
		if not isinstance(self.results, list):
			url = self.results.get_url(index)
			title = self.results.get_title(index)
		else:
			url = self.results[index]["url"]
			title = self.results[index]["title"]
		self.player.media.stop()
		if hasattr(self, "description"):
			del self.description 
		if hasattr(self, "comments"):
			del self.comments
		try:
			stream = get_video_stream(url) if not self.audio_mode else get_audio_stream(url)
		except Exception:
			logger.exception("Could not change track. index=%s url=%s", index, url)
			return
		self.player.set_media(stream.url)
		self.url = url
		self.title = title
		self.record_history(self.get_history_data_for_index(index, title, url))
		wx.CallAfter(self.SetTitle, f"{title} - {application.name}")
		self.player.media.play()
		self.player.media.audio_set_volume(self.player.volume)
		self.player.apply_saved_audio_output_device()
		Thread(target=self.extract_description).start()
		Thread(target=self.extract_comments).start()

	def next(self):
		if self.results is None:
			return
		index = 0 if self.current_index is None else self.current_index+1
		if index >= self.get_result_count():
			return
		self.current_index = index
		self.changeTrack(index)
		self.maybe_load_more_results(index)

	def previous(self):
		if self.results is None:
			return
		if self.current_index is None or self.current_index == 0:
			return
		self.current_index -= 1
		self.changeTrack(self.current_index)

	def onCopy(self, event):
		pyperclip.copy(self.url)
		wx.MessageBox(_("video URL has been copyed successfully."), _("done"), parent=self)

	def onBrowser(self, event):
		speak(_("opening"))
		webbrowser.open(self.url)

	@has_player
	def onAudioOutputDevice(self, event):
		devices = self.player.get_audio_output_devices()
		selected_device = self.player.get_selected_audio_output_device()
		dlg = AudioOutputDeviceDialog(self, devices, selected_device)
		try:
			if dlg.ShowModal() != wx.ID_OK:
				return
			device = dlg.get_selected_device()
			if self.player.select_audio_output_device(device["id"]):
				speak(_("audio output device changed to {}").format(device["description"]))
			else:
				speak(_("selected audio output device is unavailable. using default audio output device"))
		finally:
			dlg.Destroy()

	def on_audio_output_fallback(self):
		wx.CallAfter(speak, _("selected audio output device is unavailable. using default audio output device"))

	def onM4aDownload(self, event):
		dlg = DownloadProgress(wx.GetApp().GetTopWindow(), self.title)
		direct_download(1, self.url, dlg, path=self.path)

	def onMp3Download(self, event):
		dlg = DownloadProgress(wx.GetApp().GetTopWindow(), self.title)
		direct_download(2, self.url, dlg, path=self.path)

	def onVideoDownload(self, event):
		dlg = DownloadProgress(wx.GetApp().GetTopWindow(), self.title)
		direct_download(0, self.url, dlg, path=self.path)


	def onDirect(self, event):
		dlg = DownloadProgress(wx.GetApp().GetTopWindow(), self.title)
		direct_download(int(config_get('defaultformat')), self.url, dlg, path=self.path)

	def onDescription(self, event):
		if hasattr(self, "description"):
			DescriptionDialog(self, self.description)
			return
		def extract_description():
			try:
				speak(_("extracting video description"))
				info = Video.getInfo(self.url)
			except Exception as e:
				logger.exception("Could not fetch video description. url=%s", self.url)
				speak(_("an error occured while extracting the video description"))
				return
			self.description = info['description']
			wx.CallAfter(DescriptionDialog, self, self.description)
		Thread(target=extract_description).start()

	def extract_description(self):
		try:
			info = Video.get(self.url)
		except Exception:
			logger.exception("Could not preload video description. url=%s", self.url)
			return
		self.description = info['description']
	def extract_comments(self):
		if not self.stream and not hasattr(self, "comments"):
			logger.info("Loading comments. url=%s", self.url)
			try:
				self.comments = extract_youtube_comments(self.url)
			except Exception:
				logger.exception("Could not fetch comments. url=%s", self.url)
				return False
		return hasattr(self, "comments")

	def onComments(self, event):
		if self.stream:
			speak(_("cannot load comments for this video"))

			return
		if not hasattr(self, "comments"):
			speak(_("loading comments"))
			def extract():
				if not self.extract_comments():
					speak(_("unable to find comments"))
					return
				wx.CallAfter(CommentsDialog, self, self.comments)
			Thread(target=extract).start()
		else:
			CommentsDialog(self, self.comments)
