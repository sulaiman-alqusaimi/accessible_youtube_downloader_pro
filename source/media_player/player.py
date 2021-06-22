
import vlc
from datetime import timedelta
from utiles import time_formatting
from threading import Thread
from settings_handler import config_get

instance = vlc.Instance()

media_player = instance.media_player_new()

class Player:
	def __init__(self,filename, hwnd):
		self.do_reset = False
		self.filename = filename
		self.hwnd = hwnd
		self.media = media_player
		self.set_media(self.filename)
		self.media.set_hwnd(self.hwnd)
		self.manager = self.media.event_manager()
		self.manager.event_attach(vlc.EventType.MediaPlayerEndReached,self.onEnd)
		self.media.play()
		self.volume = self.media.audio_get_volume()
	def onEnd(self,event):
		if event.type == vlc.EventType.MediaPlayerEndReached:
			self.do_reset = True
			Thread(target=self.reset).start()
	def seek(self, seconds):
		length = self.media.get_length()
		if length == -1:
			return 0.03
		try:
			return seconds/(self.media.get_length()/1000)
		except ZeroDivisionError:
			return 0.03
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
		if config_get("repeatetracks"):
			self.media.play()

	def set_media(self, m):
		media = instance.media_new(m)
		self.media.set_media(media)
