import os
os.add_dll_directory(os.getcwd())
import vlc


class Player:
	def __init__(self,filename, hwnd):
		self.do_reset = False
		self.filename = filename
		self.hwnd = hwnd
		self.media = vlc.MediaPlayer(self.filename)
		self.media.set_hwnd(self.hwnd)
		self.manager = self.media.event_manager()
		self.manager.event_attach(vlc.EventType.MediaPlayerEndReached,self.onEnd)
		self.media.play()
	def onEnd(self,event):
		if event.type == vlc.EventType.MediaPlayerEndReached:
			self.do_reset = True
	def seek(self, seconds):
		length = self.media.get_length()
		if length == -1:
			return 0.03
		try:
			return seconds/(self.media.get_length()/1000)
		except ZeroDivisionError:
			return 0.03

	def reset(self):
		self.media.set_media(self.media.get_media())
		self.media.play()
		self.do_reset = False
