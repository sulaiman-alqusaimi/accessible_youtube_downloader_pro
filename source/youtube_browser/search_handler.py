from youtubesearchpython import VideosSearch, CustomSearch
from dialogs.search_dialog import SearchDialog
from language_handler import init_translation

try:
	init_translation("accessible_youtube_downloader")
except:
	_ = lambda msg: msg

class Search:
	def __init__(self, query, filter=0):
		self.query = query
		self.filter = filter
		self.results = {}
		self.count = 1
		filters = {
			1: "EgJAAQ",
			2: "CAISAhAB",
			3: "CAMSAhAB"}
		if self.filter == 0:
			self.videos = VideosSearch(self.query)
		else:
			self.videos = CustomSearch(self.query, filters[self.filter])
		self.parse_results()

	def parse_results(self):
		results = self.videos.result()["result"]
		for result in results:
			self.results[self.count] = {"title": result["title"], "url": f"https://www.youtube.com/watch?v={result['id']}", "views": self.parse_views(result["viewCount"]["text"]), "channel": {"name": result["channel"]["name"], "url": f"https://www.youtube.com/channel/{result['channel']['id']}"}, "duration": result["duration"]}
			self.count += 1
	def get_titles(self):
		return [f"{self.results[result]['title']},{self.get_duration(self.results[result]['duration'])} {_('بواسطة')} {self.results[result]['channel']['name']}, {self.views_part(self.results[result]['views'])}" for result in self.results]
	def get_last_titles(self):
		titles = self.get_titles()
		return titles[len(titles)-self.new_videos:len(titles)]
	def get_title(self, number):
		return self.results[number+1]["title"]
	def get_url(self, number):
		return self.results[number+1]["url"]
	def load_more(self):
		try:
			self.videos.next()
		except:
			return
		current = self.count
		self.parse_results()
		self.new_videos = self.count-current
		return True
	def parse_views(self, string):
		try:
			string = string.replace(",", "")
		except AttributeError:
			return
		return string.replace("views", "")
	def get_views(self, number):

		return self.results[number+1]['views']
	def views_part(self, data):
		if data is not None:
			return _("عدد المشاهدات {}").format(data)
		else:
			return _("بث مباشر")
	def time_formatting(self, t):
		t = t.split(":")
		t = [int(i) for i in t]
		def minute(m):
			if m == 1:
				return _("دقيقة واحدة")
			elif m == 2:
				return _("دقيقتان")
			elif m >=3 and m <=10:
				return _("{} دقائق").format(m)
			else:
				return _("{} دقيقة").format(m)
		def second(s):
			if s == 1:
				return _("ثانية")
			elif s == 2:
				return _("ثانيتين")
			elif s >= 3 and s <= 10:
				return _("{} ثواني").format(s)
			else:
				return _("{} ثانية").format(s)
		def hour(h):
			if h == 1:
				return _("ساعة")
			elif h == 2:
				return _("ساعتان")
			elif h >= 3 and h <=10:
				return _("{} ساعات").format(h)
			else:
				return _("{} ساعة").format(h)
		if len(t) == 1:
			return second(t[0])
		elif len(t) == 2:
			return _("{} و{}").format(minute(t[0]), second(t[1]))
		elif len(t) == 3:
			return _("{} و{} و{}").format(hour(t[0]), minute(t[1]), second(t[2]))

	def get_duration(self, data): # get the duration of the video
		if data is not None:
			return _(" المدة: {},").format(self.time_formatting(data))
		else:
			return ""