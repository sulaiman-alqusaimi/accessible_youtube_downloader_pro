
import vlc
from datetime import timedelta
from utiles import time_formatting
from threading import Thread
from time import sleep
from settings_handler import config_get, config_set
from app_logger import get_logger


logger = get_logger()

instance = vlc.Instance()

media_player = instance.media_player_new()

DEFAULT_AUDIO_OUTPUT_DEVICE = ""

class Player:
	def __init__(self,filename, hwnd, window=None):
		logger.info("Creating VLC player. hwnd=%s media=%s", hwnd, filename)
		self.do_reset = False
		self.window = window
		self.filename = filename
		self.hwnd = hwnd
		self.media = media_player
		self.set_media(self.filename)
		self.media.set_hwnd(self.hwnd)
		self.manager = self.media.event_manager()
		self.manager.event_attach(vlc.EventType.MediaPlayerEndReached,self.onEnd)
		self.manager.event_attach(vlc.EventType.MediaPlayerEncounteredError,self.onError)
		self.media.play()
		self.volume = int(config_get("volume"))
		self.media.audio_set_volume(self.volume)
		self.apply_saved_audio_output_device()
	def onEnd(self,event):
		if event.type == vlc.EventType.MediaPlayerEndReached:
			logger.info("Media playback ended")
			self.do_reset = True
			Thread(target=self.reset).start()
	def onError(self,event):
		if event.type == vlc.EventType.MediaPlayerEncounteredError and self.get_selected_audio_output_device():
			logger.warning("VLC reported an error while a custom audio output device was selected")
			self.reset_audio_output_device_to_default(notify=True)
	def seek(self, seconds):
		length = self.media.get_length()
		if length == -1:
			return 0.03
		try:
			return seconds/(self.media.get_length()/1000)
		except ZeroDivisionError:
			return 0.03

	def seek_seconds(self, seconds):
		position = self.media.get_position()
		step = self.seek(abs(seconds))
		if seconds < 0:
			step = -step
		self.media.set_position(max(0.0, min(1.0, position+step)))
	def get_duration(self):
		duration = self.media.get_length()
		if duration == -1 or not isinstance(duration, int):
			return ""
		return time_formatting(str(timedelta(seconds=duration//1000)))
	def get_elapsed(self):
		elapsed = self.media.get_time()
		if elapsed == -1 or not isinstance(elapsed, int):
			return ""
		return time_formatting(str(timedelta(seconds=elapsed//1000)))

	def reset(self):
		self.do_reset = False
		self.media.set_media(self.media.get_media())
		if config_get("repeatetracks") and not config_get('autonext'):
			logger.info("Repeating current track")
			self.media.play()
			self.apply_saved_audio_output_device()
		elif config_get('autonext') and not config_get('repeatetracks'):
			logger.info("Auto-playing next track")
			self.window.next()


	def set_media(self, m):
		logger.info("Setting VLC media: %s", m)
		media = instance.media_new(m)
		self.media.set_media(media)

	def _decode_vlc_string(self, value):
		if isinstance(value, bytes):
			return value.decode("utf-8", errors="replace")
		if value is None:
			return ""
		return str(value)

	def get_audio_output_devices(self):
		devices = []
		seen = set()
		device_list = None
		try:
			device_list = self.media.audio_output_device_enum()
			current = device_list
			while current:
				item = current.contents
				device_id = self._decode_vlc_string(item.device)
				description = self._decode_vlc_string(item.description) or device_id
				if device_id and device_id not in seen:
					devices.append({"id": device_id, "description": description})
					seen.add(device_id)
				current = item.next
		except Exception:
			logger.exception("Could not enumerate VLC audio output devices")
		finally:
			if device_list:
				try:
					vlc.libvlc_audio_output_device_list_release(device_list)
				except Exception:
					logger.exception("Could not release VLC audio output device list")
		return devices

	def get_selected_audio_output_device(self):
		device_id = config_get("audiooutputdevice")
		if device_id is None or device_id == "None":
			return DEFAULT_AUDIO_OUTPUT_DEVICE
		return str(device_id)

	def get_current_audio_output_device(self):
		try:
			device_id = self.media.audio_output_device_get()
		except Exception:
			logger.exception("Could not get current VLC audio output device")
			return None
		return self._decode_vlc_string(device_id)

	def _get_audio_output_device_connection_status(self, device_id):
		devices = self.get_audio_output_devices()
		if not devices:
			logger.info("VLC did not return audio output devices; keeping configured device. device_id=%s", device_id)
			return None
		return any(device["id"] == device_id for device in devices)

	def apply_saved_audio_output_device(self):
		device_id = self.get_selected_audio_output_device()
		if not device_id:
			logger.info("No custom audio output device configured; using system default")
			return True
		Thread(target=self._restore_saved_audio_output_device, args=(device_id,)).start()
		return True

	def _restore_saved_audio_output_device(self, device_id):
		for attempt in range(1, 6):
			if self.get_selected_audio_output_device() != device_id:
				return
			is_last_attempt = attempt == 5
			logger.info("Restoring saved audio output device. attempt=%s device_id=%s", attempt, device_id)
			self.select_audio_output_device(
				device_id,
				notify_on_fallback=is_last_attempt,
				reset_on_failure=is_last_attempt,
			)
			if not is_last_attempt:
				sleep(0.7)

	def select_audio_output_device(self, device_id, notify_on_fallback=False, reset_on_failure=True):
		device_id = device_id or DEFAULT_AUDIO_OUTPUT_DEVICE
		if device_id == DEFAULT_AUDIO_OUTPUT_DEVICE:
			return self.reset_audio_output_device_to_default()
		connection_status = self._get_audio_output_device_connection_status(device_id)
		if connection_status is False:
			logger.warning("Selected audio output device is not connected. device_id=%s", device_id)
			if reset_on_failure:
				self.reset_audio_output_device_to_default(notify=notify_on_fallback)
			return False
		try:
			self.media.audio_output_device_set(None, device_id)
		except Exception:
			logger.exception("Could not select VLC audio output device. device_id=%s", device_id)
			if reset_on_failure:
				self.reset_audio_output_device_to_default(notify=notify_on_fallback)
			return False
		logger.info("Selected audio output device. device_id=%s", device_id)
		config_set("audiooutputdevice", device_id)
		return True

	def reset_audio_output_device_to_default(self, notify=False):
		try:
			self.media.audio_output_device_set(None, None)
			self._restart_audio_output()
		except Exception:
			logger.exception("Could not reset VLC audio output device to default")
		logger.info("Using default audio output device")
		config_set("audiooutputdevice", DEFAULT_AUDIO_OUTPUT_DEVICE)
		if notify:
			self._notify_audio_output_fallback()
		return True

	def _restart_audio_output(self):
		state = self.media.get_state()
		if state not in (vlc.State.Playing, vlc.State.Paused):
			return
		position = self.media.get_position()
		was_playing = state == vlc.State.Playing
		self.media.stop()
		self.media.play()
		if position not in (-1, 0.0):
			self.media.set_position(position)
		if not was_playing:
			self.media.pause()
		self.media.audio_set_volume(self.volume)

	def _notify_audio_output_fallback(self):
		if self.window is not None and hasattr(self.window, "on_audio_output_fallback"):
			self.window.on_audio_output_fallback()
