import re
from urllib.parse import quote_plus, urlsplit, urlunsplit

import yt_dlp as youtube_dl
from youtubesearchpython import VideosSearch, CustomSearch
from download_handler.downloader import get_yt_dlp_options, is_browser_cookie_error
from utiles import format_views, friendly_upload_date, time_formatting
from app_logger import get_logger


logger = get_logger()

PLAYLIST_SEARCH_FILTER = "EgIQAw%253D%253D"
CHANNEL_SEARCH_FILTER = "EgIQAg%253D%253D"
VIDEO_SEARCH_FILTER = "EgIQAQ%253D%253D"


def channel_videos_url(url):
	parts = urlsplit(url)
	path = parts.path.rstrip("/")
	if path.endswith("/videos"):
		return urlunsplit((parts.scheme, parts.netloc, path, "", ""))
	if path.startswith(("/channel/", "/c/", "/user/", "/@")):
		path = f"{path}/videos"
	return urlunsplit((parts.scheme, parts.netloc, path, "", ""))


def duration_text(value):
	if value in (None, ""):
		return ""
	if isinstance(value, str):
		return time_formatting(value) if ":" in value else value
	try:
		seconds = int(value)
	except (TypeError, ValueError):
		return str(value)
	minutes, seconds = divmod(seconds, 60)
	hours, minutes = divmod(minutes, 60)
	if hours:
		return time_formatting(f"{hours}:{minutes:02d}:{seconds:02d}")
	return time_formatting(f"{minutes}:{seconds:02d}")


class PlaylistResult:
	def __init__(self, url, title=""):
		logger.info("Loading playlist. url=%s", url)
		self.url = url
		self.title = title
		self.videos = []
		self.seen_urls = set()
		self.count = 0
		self.batch_size = 30
		self.has_more_videos = True
		self.new_videos = 0
		self.load()

	def load(self):
		start = self.count+1
		end = self.count+self.batch_size
		try:
			info = self.extract(start, end, use_cookies=True)
		except youtube_dl.utils.DownloadError as e:
			if not is_browser_cookie_error(e):
				logger.exception("Could not load playlist. url=%s", self.url)
				raise
			logger.warning("Cookie-based playlist load failed; retrying without cookies. url=%s error=%s", self.url, e)
			info = self.extract(start, end, use_cookies=False)
		self.title = self.title or info.get("title") or _("playlist")
		entries = list(info.get("entries") or [])
		current = len(self.videos)
		for entry in entries:
			video = self.normalize_video(entry)
			if video is not None and video["url"] not in self.seen_urls:
				self.seen_urls.add(video["url"])
				self.videos.append(video)
		self.count += len(entries)
		self.new_videos = len(self.videos)-current
		if len(entries) < self.batch_size or self.new_videos == 0:
			self.has_more_videos = False

	def extract(self, start, end, use_cookies=True):
		options = {
			"quiet": True,
			"no_warnings": True,
			"skip_download": True,
			"extract_flat": "in_playlist",
			"playliststart": start,
			"playlistend": end,
		}
		options.update(get_yt_dlp_options(use_cookies=use_cookies))
		with youtube_dl.YoutubeDL(options) as ydl:
			return ydl.extract_info(self.url, download=False)

	def normalize_video(self, entry):
		if not entry:
			return
		video_id = entry.get("id")
		url = entry.get("webpage_url") or entry.get("url")
		if url and url.startswith("/"):
			url = f"https://www.youtube.com{url}"
		elif url and not url.startswith(("http://", "https://")):
			url = f"https://www.youtube.com/watch?v={url}"
		elif not url and video_id:
			url = f"https://www.youtube.com/watch?v={video_id}"
		if not url:
			return
		channel_name = entry.get("channel") or entry.get("uploader") or self.title
		channel_url = entry.get("channel_url") or entry.get("uploader_url") or ""
		return {
			"title": entry.get("title") or _("unknown"),
			"url": url,
			"duration": duration_text(entry.get("duration") or entry.get("duration_string")),
			"channel": {
				"name": channel_name,
				"url": channel_url,
			},
		}

	def next(self):
		if not self.has_more_videos:
			self.new_videos = 0
			return False
		logger.info("Loading more playlist videos. url=%s", self.url)
		self.load()
		return self.new_videos > 0
	def get_new_titles(self):
		titles = self.get_display_titles()
		return titles[len(titles)-self.new_videos:len(titles)]

	def get_title(self, n):
		return self.videos[n]["title"]
	def get_display_titles(self):
		titles = []
		for vid in self.videos:
			title = [
				vid["title"],
				_("duration: {}").format(vid["duration"]) if vid["duration"] else "",
				f"{_('from')} {vid['channel']['name']}",
			]
			titles.append(", ".join([element for element in title if element != ""]))
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


class ChannelResult:
	def __init__(self, url, title=""):
		logger.info("Loading channel videos. url=%s", url)
		self.source_url = url
		self.url = channel_videos_url(url)
		self.title = title
		self.videos = []
		self.seen_urls = set()
		self.count = 0
		self.batch_size = 30
		self.has_more_videos = True
		self.new_videos = 0
		self.load()

	def load(self):
		start = self.count+1
		end = self.count+self.batch_size
		try:
			info = self.extract(start, end, use_cookies=True)
		except youtube_dl.utils.DownloadError as e:
			if not is_browser_cookie_error(e):
				logger.exception("Could not load channel videos. url=%s", self.url)
				raise
			logger.warning("Cookie-based channel load failed; retrying without cookies. url=%s error=%s", self.url, e)
			info = self.extract(start, end, use_cookies=False)
		self.title = self.title or info.get("channel") or info.get("uploader") or info.get("title") or _("channel")
		entries = list(info.get("entries") or [])
		current = len(self.videos)
		for entry in entries:
			video = self.normalize_video(entry)
			if video is not None and video["url"] not in self.seen_urls:
				self.seen_urls.add(video["url"])
				self.videos.append(video)
		self.count += len(entries)
		self.new_videos = len(self.videos)-current
		if len(entries) < self.batch_size or self.new_videos == 0:
			self.has_more_videos = False

	def extract(self, start, end, use_cookies=True):
		options = {
			"quiet": True,
			"no_warnings": True,
			"skip_download": True,
			"extract_flat": "in_playlist",
			"playliststart": start,
			"playlistend": end,
		}
		options.update(get_yt_dlp_options(use_cookies=use_cookies))
		with youtube_dl.YoutubeDL(options) as ydl:
			return ydl.extract_info(self.url, download=False)

	def normalize_video(self, entry):
		if not entry:
			return
		video_id = entry.get("id")
		url = entry.get("webpage_url") or entry.get("url")
		if url and url.startswith("/"):
			url = f"https://www.youtube.com{url}"
		elif url and not url.startswith(("http://", "https://")):
			url = f"https://www.youtube.com/watch?v={url}"
		elif not url and video_id:
			url = f"https://www.youtube.com/watch?v={video_id}"
		if not url:
			return
		channel_name = entry.get("channel") or entry.get("uploader") or self.title
		channel_url = entry.get("channel_url") or entry.get("uploader_url") or self.source_url
		return {
			"title": entry.get("title") or _("unknown"),
			"url": url,
			"duration": duration_text(entry.get("duration") or entry.get("duration_string")),
			"views": entry.get("view_count"),
			"upload_date": friendly_upload_date(entry.get("upload_date") or entry.get("timestamp")),
			"channel": {
				"name": channel_name,
				"url": channel_url,
			},
		}

	def next(self):
		if not self.has_more_videos:
			return False
		logger.info("Loading more channel videos. url=%s", self.url)
		self.load()
		return self.new_videos > 0

	def get_new_titles(self):
		titles = self.get_display_titles()
		return titles[len(titles)-self.new_videos:len(titles)]

	def get_title(self, n):
		return self.videos[n]["title"]

	def get_display_titles(self):
		titles = []
		for vid in self.videos:
			title = [
				vid["title"],
				_("duration: {}").format(vid["duration"]) if vid["duration"] else "",
				f"{_('from')} {vid['channel']['name']}",
				format_views(vid["views"]),
				vid["upload_date"],
			]
			titles.append(", ".join([element for element in title if element != ""]))
		return titles

	def get_url(self, n):
		return self.videos[n]["url"]

	def get_history_data(self, n):
		video = self.videos[n]
		return {
			"title": video["title"],
			"url": video["url"],
			"views": video["views"],
			"upload_date": video["upload_date"],
			"channel_name": video["channel"]["name"],
			"channel_url": video["channel"]["url"],
		}


class PlaylistSearch:
	def __init__(self, query, limit=20):
		logger.info("Creating playlist search. query=%s", query)
		self.query = query
		self.limit = limit
		self.results = []
		self.count = 0
		self.has_more = True
		self.next()

	def result(self):
		return {"result": self.results}

	def next(self):
		if not self.has_more:
			return False
		start = self.count+1
		end = self.count+self.limit
		try:
			info = self.extract(start, end, use_cookies=True)
		except youtube_dl.utils.DownloadError as e:
			if not is_browser_cookie_error(e):
				logger.exception("Could not load playlist search results. query=%s", self.query)
				raise
			logger.warning("Cookie-based playlist search failed; retrying without cookies. query=%s error=%s", self.query, e)
			info = self.extract(start, end, use_cookies=False)
		entries = list(info.get("entries") or [])
		page_results = []
		for entry in entries:
			result = self.normalize_playlist(entry)
			if result is not None:
				page_results.append(result)
		self.count += len(entries)
		self.results = page_results
		self.has_more = len(entries) >= self.limit and len(page_results) > 0
		return len(page_results) > 0

	def extract(self, start, end, use_cookies=True):
		url = f"https://www.youtube.com/results?search_query={quote_plus(self.query)}&sp={PLAYLIST_SEARCH_FILTER}"
		options = {
			"quiet": True,
			"no_warnings": True,
			"skip_download": True,
			"extract_flat": "in_playlist",
			"playliststart": start,
			"playlistend": end,
		}
		options.update(get_yt_dlp_options(use_cookies=use_cookies))
		with youtube_dl.YoutubeDL(options) as ydl:
			return ydl.extract_info(url, download=False)

	def normalize_playlist(self, entry):
		if not entry:
			return
		playlist_id = entry.get("id")
		url = entry.get("webpage_url") or entry.get("url")
		if url and url.startswith("/"):
			url = f"https://www.youtube.com{url}"
		elif url and not url.startswith(("http://", "https://")):
			url = f"https://www.youtube.com/playlist?list={url}"
		elif not url and playlist_id:
			url = f"https://www.youtube.com/playlist?list={playlist_id}"
		if not url:
			return
		return {
			"type": "playlist",
			"id": playlist_id,
			"title": entry.get("title") or _("unknown"),
			"link": url,
			"videoCount": entry.get("playlist_count") or entry.get("n_entries"),
			"channel": {
				"name": entry.get("channel") or entry.get("uploader") or _("unknown"),
				"id": None,
				"link": entry.get("channel_url") or entry.get("uploader_url"),
			},
		}


class ChannelSearch(PlaylistSearch):
	def __init__(self, query, limit=20):
		logger.info("Creating channel search. query=%s", query)
		self.query = query
		self.limit = limit
		self.results = []
		self.count = 0
		self.has_more = True
		self.next()

	def extract(self, start, end, use_cookies=True):
		url = f"https://www.youtube.com/results?search_query={quote_plus(self.query)}&sp={CHANNEL_SEARCH_FILTER}"
		options = {
			"quiet": True,
			"no_warnings": True,
			"skip_download": True,
			"extract_flat": "in_playlist",
			"playliststart": start,
			"playlistend": end,
		}
		options.update(get_yt_dlp_options(use_cookies=use_cookies))
		with youtube_dl.YoutubeDL(options) as ydl:
			return ydl.extract_info(url, download=False)

	def normalize_playlist(self, entry):
		if not entry:
			return
		channel_id = entry.get("channel_id") or entry.get("id")
		url = entry.get("webpage_url") or entry.get("channel_url") or entry.get("url")
		if url and url.startswith("/"):
			url = f"https://www.youtube.com{url}"
		elif url and not url.startswith(("http://", "https://")):
			url = f"https://www.youtube.com/channel/{url}"
		elif not url and channel_id:
			url = f"https://www.youtube.com/channel/{channel_id}"
		if not url:
			return
		title = entry.get("channel") or entry.get("uploader") or entry.get("title") or _("unknown")
		return {
			"type": "channel",
			"id": channel_id,
			"title": title,
			"link": url,
			"videoCount": None,
			"channel": {
				"name": title,
				"id": channel_id,
				"link": url,
			},
		}


class VideoSearch:
	def __init__(self, query, limit=20):
		logger.info("Creating yt-dlp video search. query=%s", query)
		self.query = query
		self.limit = limit
		self.results = []
		self.count = 0
		self.has_more = True
		self.next()

	def result(self):
		return {"result": self.results}

	def next(self):
		if not self.has_more:
			return False
		start = self.count+1
		end = self.count+self.limit
		try:
			info = self.extract(start, end, use_cookies=True)
		except youtube_dl.utils.DownloadError as e:
			if not is_browser_cookie_error(e):
				logger.exception("Could not load yt-dlp video search results. query=%s", self.query)
				raise
			logger.warning("Cookie-based yt-dlp video search failed; retrying without cookies. query=%s error=%s", self.query, e)
			info = self.extract(start, end, use_cookies=False)
		entries = list(info.get("entries") or [])
		page_results = []
		for entry in entries:
			result = self.normalize_video(entry)
			if result is not None:
				page_results.append(result)
		self.count += len(entries)
		self.results = page_results
		self.has_more = len(entries) >= self.limit and len(page_results) > 0
		return len(page_results) > 0

	def extract(self, start, end, use_cookies=True):
		url = f"https://www.youtube.com/results?search_query={quote_plus(self.query)}&sp={VIDEO_SEARCH_FILTER}"
		options = {
			"quiet": True,
			"no_warnings": True,
			"skip_download": True,
			"extract_flat": "in_playlist",
			"playliststart": start,
			"playlistend": end,
		}
		options.update(get_yt_dlp_options(use_cookies=use_cookies))
		with youtube_dl.YoutubeDL(options) as ydl:
			return ydl.extract_info(url, download=False)

	def normalize_video(self, entry):
		if not entry:
			return
		video_id = entry.get("id")
		url = entry.get("webpage_url") or entry.get("url")
		if url and url.startswith("/"):
			url = f"https://www.youtube.com{url}"
		elif url and not url.startswith(("http://", "https://")):
			url = f"https://www.youtube.com/watch?v={url}"
		elif not url and video_id:
			url = f"https://www.youtube.com/watch?v={video_id}"
		if not url:
			return
		return {
			"type": "video",
			"id": video_id,
			"title": entry.get("title") or _("unknown"),
			"link": url,
			"duration": entry.get("duration") or entry.get("duration_string"),
			"viewCount": entry.get("view_count"),
			"publishedTime": entry.get("upload_date") or entry.get("timestamp"),
			"channel": {
				"name": entry.get("channel") or entry.get("uploader") or _("unknown"),
				"id": None,
				"link": entry.get("channel_url") or entry.get("uploader_url"),
			},
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
		}
		try:
			if self.filter == 0:
				self.search = VideosSearch(self.query)
			elif self.filter == 4:
				self.search = PlaylistSearch(self.query)
			elif self.filter == 5:
				self.search = ChannelSearch(self.query)
			else:
				self.search = CustomSearch(self.query, filters[self.filter])
		except TypeError as e:
			if self.filter != 0:
				raise
			logger.warning("Primary YouTube video search parser failed; falling back to yt-dlp. query=%s error=%s", self.query, e)
			self.search = VideoSearch(self.query)
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
					"name": self.get_channel_name(result),
					"url": self.get_channel_url(result)}
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
		elif data["type"] == "playlist":
			title = [
				data["title"],
				_("playlist"),
				f"{_('from')} {data['channel']['name']}" if data["channel"]["name"] != _("unknown") else "",
				_("contains {} videos").format(data["elements"]) if data["elements"] is not None else "",
			]
		else:
			title = [data["title"], _("channel")]
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
	def get_channel_name(self, result):
		return result.get("channel", {}).get("name") or _("unknown")
	def get_channel_url(self, result):
		channel = result.get("channel") or {}
		if channel.get("link"):
			return channel["link"]
		if channel.get("id"):
			return f"https://www.youtube.com/channel/{channel['id']}"
		return ""
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
			if not self.search.next():
				return
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
			return _("duration: {}").format(duration_text(data))
		else:
			return ""
