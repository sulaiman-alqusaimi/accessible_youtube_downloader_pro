import re

from youtubesearchpython import VideosSearch, CustomSearch, PlaylistsSearch, PlaylistsSearch, Playlist
from utiles import format_views, friendly_upload_date, time_formatting
from app_logger import get_logger


logger = get_logger()


class PlaylistResult:
	def __init__(self, url):
		logger.info("Loading playlist. url=%s", url)
		self.url = url
		self.playlist = Playlist(url)
		self.videos = []
		self.count = 0
		self.parse()

	def parse(self):
		for vid in self.playlist.videos[self.count:]:
			video = {
				"title": vid["title"],
				"url": f"https://youtube.com/watch?v={vid['id']}",
				"duration": time_formatting(vid["duration"]),
				"channel": {
					"name": vid["channel"]["name"], 
					"url": f"https://www.youtube.com/channel/{vid['channel']['id']}"},

			}
			self.videos.append(video)
			self.count = len(self.videos)

	def next(self):
		if not self.playlist.hasMoreVideos:
			return
		logger.info("Loading more playlist videos. url=%s", self.url)
		self.playlist.getNextVideos()
		current = self.count
		self.parse()
		self.new_videos = self.count-current

		return True
	def get_new_titles(self):
		titles = self.get_display_titles()
		return titles[len(titles)-self.new_videos:len(titles)]

	def get_title(self, n):
		return self.videos[n]["title"]
	def get_display_titles(self):
		titles = []
		for vid in self.videos:
			title = [vid['title'], _("duration: {}").format(vid['duration']), f"{_("from")} {vid['channel']['name']}"]
			titles.append(", ".join(title))
		return titles
	def get_url(self, n):
		return self.videos[n]["url"]
	def get_history_data(self, n):
		video = self.videos[n]
		return {
			"title": video["title"],
			"url": video["url"],
			"channel_name": video["channel"]["name"],
			"channel_url": video["channel"]["url"],
		}





class Search:
	def __init__(self, query, filter=0):
		logger.info("Creating search. query=%s filter=%s", query, filter)
		self.query = query
		self.filter = filter
		self.results = {}
		self.count = 1
		filters = {
			1: "EgJAAQ",
			2: "CAISAhAB",
			3: "CAMSAhAB", 
			4: "EgIQA"
		}
		if self.filter == 0:
			self.search = VideosSearch(self.query)
		elif self.filter == 4:
				self.search = PlaylistsSearch(self.query)
		else:
			self.search = CustomSearch(self.query, filters[self.filter])
		self.parse_results()

	def parse_results(self):
		results = self.search.result()["result"]
		for result in results:
			self.results[self.count] = {
				"type": result["type"],
				"title": result["title"],
				"url": result["link"], 
				"duration": result.get("duration"),
				"elements": result.get("videoCount"),
				"upload_date": friendly_upload_date(result.get("publishedTime")),
				"channel": {
					"name": result["channel"]["name"], 
					"url": f"https://www.youtube.com/channel/{result['channel']['id']}"}
			}
			if result["type"] == "video":
				self.results[self.count]["views"] = self.parse_views(result.get("viewCount"))
			else:
				self.results[self.count]["views"] = None
			self.count += 1
	def get_titles(self):
		titles = []
		for result, data  in self.results.items():
			titles.append(self.get_display_title(data))
		return titles

	def get_display_title(self, data):
		if data["type"] == "video":
			title = [
				data["title"],
				self.get_duration(data["duration"]),
				f"{_('from')} {data['channel']['name']}",
				self.views_part(data["views"]),
				data["upload_date"],
			]
		else:
			title = [
				data["title"],
				_("playlist"),
				f"{_('from')} {data['channel']['name']}",
				_("contains {} videos").format(data["elements"]),
			]
		return ", ".join([element for element in title if element != ""])

	def get_last_titles(self):
		titles = self.get_titles()
		return titles[len(titles)-self.new_videos:len(titles)]
	def get_title(self, number):
		return self.results[number+1]["title"]
	def get_url(self, number):
		return self.results[number+1]["url"]
	def get_type(self, number):
		return self.results[number+1]["type"]
	def get_channel(self, number):
		return self.results[number+1]["channel"]
	def get_history_data(self, number):
		data = self.results[number+1]
		return {
			"title": data["title"],
			"display_title": self.get_display_title(data),
			"url": data["url"],
			"views": data["views"],
			"upload_date": data["upload_date"],
			"channel_name": data["channel"]["name"],
			"channel_url": data["channel"]["url"],
		}

	def load_more(self):
		try:
			logger.info("Loading more search results. query=%s", self.query)
			self.search.next()
		except Exception:
			logger.exception("Could not load more search results. query=%s", self.query)
			return
		current = self.count
		self.parse_results()
		self.new_videos = self.count-current
		return True
	def parse_views(self, data):
		if isinstance(data, dict):
			data = data.get("text") or data.get("short")
		if data is None:
			return
		if isinstance(data, (int, float)):
			return int(data)
		text = str(data)
		match = re.search(r"([\d,.]+)\s*([kmbKMB]?)", text)
		if match is None:
			return
		try:
			number = float(match.group(1).replace(",", ""))
			multiplier = {"k": 1000, "m": 1000000, "b": 1000000000}.get(match.group(2).lower(), 1)
			return int(number*multiplier)
		except ValueError:
			return match.group(1)
	def get_views(self, number):

		return self.results[number+1]['views']
	def views_part(self, data):
		if data is not None:
			return format_views(data)
		else:
			return _("lives")

	def get_duration(self, data): # get the duration of the video
		if data is not None:
			return _("duration: {}").format(time_formatting(data))
		else:
			return ""
