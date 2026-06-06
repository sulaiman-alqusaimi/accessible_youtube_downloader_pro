import re
from datetime import datetime, timezone
from threading import Thread
from settings_handler import config_get
from download_handler.downloader import downloadAction, get_yt_dlp_options, is_browser_cookie_error
from app_logger import get_logger
import json
import requests
import wx
import application
import yt_dlp as youtube_dl


logger = get_logger()


def format_count(value):
	try:
		if value is None or value == "":
			return ""
		if isinstance(value, str):
			return value.strip()
		return f"{int(value):,}"
	except (TypeError, ValueError):
		return str(value)


def format_views(value):
	value = format_count(value)
	if value:
		return _("{} views").format(value)
	return ""


def relative_time_part(value):
	if value is None or value == "":
		return ""
	if isinstance(value, str):
		text = value.strip()
		if text == "":
			return ""
		lower_text = text.lower()
		for prefix in ("streamed ", "premiered ", "uploaded "):
			if lower_text.startswith(prefix):
				text = text[len(prefix):].strip()
				lower_text = text.lower()
		if lower_text.endswith(" ago"):
			text = text[:-4].strip()
			lower_text = text.lower()
		if lower_text in ("just now", "today"):
			return _("just now")
		date_value = parse_date_value(text)
		if date_value is not None:
			return relative_time_from_datetime(date_value)
		match = re.search(r"(\d+)\s+([a-zA-Z]+)", text)
		if match:
			amount = int(match.group(1))
			unit = match.group(2).lower()
			return format_time_unit(amount, unit)
		return text
	if isinstance(value, (int, float)):
		if value > 1000000000:
			return relative_time_from_datetime(datetime.fromtimestamp(value, timezone.utc))
	return str(value)


def parse_date_value(value):
	for date_format in ("%Y%m%d", "%Y-%m-%d", "%Y/%m/%d"):
		try:
			return datetime.strptime(value, date_format).replace(tzinfo=timezone.utc)
		except ValueError:
			pass
	try:
		return datetime.fromisoformat(value.replace("Z", "+00:00"))
	except ValueError:
		return None


def relative_time_from_datetime(date_value):
	if date_value.tzinfo is None:
		date_value = date_value.replace(tzinfo=timezone.utc)
	now = datetime.now(timezone.utc)
	seconds = max(0, int((now-date_value).total_seconds()))
	minutes = seconds//60
	if minutes < 1:
		return _("just now")
	if minutes < 60:
		return format_time_unit(minutes, "minute")
	hours = minutes//60
	if hours < 24:
		return format_time_unit(hours, "hour")
	days = hours//24
	if days < 7:
		return format_time_unit(days, "day")
	if days < 30:
		return format_time_unit(days//7, "week")
	if days < 365:
		return format_time_unit(days//30, "month")
	return format_time_unit(days//365, "year")


def format_time_unit(amount, unit):
	unit = unit.rstrip("s")
	labels = {
		"minute": (_("1 minute"), _("{} minutes")),
		"min": (_("1 minute"), _("{} minutes")),
		"hour": (_("1 hour"), _("{} hours")),
		"day": (_("1 day"), _("{} days")),
		"week": (_("1 week"), _("{} weeks")),
		"month": (_("1 month"), _("{} months")),
		"year": (_("1 year"), _("{} years")),
	}
	singular, plural = labels.get(unit, (f"1 {unit}", f"{{}} {unit}s"))
	if amount == 1:
		return singular
	return plural.format(amount)


def friendly_upload_date(value):
	time_part = relative_time_part(value)
	if time_part:
		return _("uploaded {} ago").format(time_part) if time_part != _("just now") else _("uploaded just now")
	return ""


def friendly_played_date(value):
	time_part = relative_time_part(value)
	if time_part:
		return _("played {} ago").format(time_part) if time_part != _("just now") else _("played just now")
	return ""


def build_video_display_title(title, channel_name="", views="", upload_date="", played_at=""):
	parts = [title]
	if channel_name:
		parts.append(f"{_('from')} {channel_name}")
	views_text = format_views(views)
	if views_text:
		parts.append(views_text)
	if upload_date:
		parts.append(upload_date)
	played_text = friendly_played_date(played_at)
	if played_text:
		parts.append(played_text)
	return ", ".join(parts)


target_video_height = 360
target_audio_bitrate = 70
min_audio_bitrate = 48
max_audio_bitrate = 96
heavy_audio_bitrate = 128
preferred_audio_format_ids = ("249", "250", "251", "140")
known_audio_bitrates = {
	"249": 50,
	"250": 70,
	"251": 160,
	"140": 128,
}


class YtdlpStream:
	def __init__(self, title, data, info=None):
		info = info or {}
		self.title = title
		self.url = data["url"]
		self.extension = data.get("ext", "")
		self.resolution = self.get_resolution(data)
		self.format_id = data.get("format_id", "")
		self.quality = get_format_quality(data)
		self.debug_description = get_format_debug_description(data)
		self.webpage_url = info.get("webpage_url") or info.get("original_url")
		self.view_count = info.get("view_count")
		self.upload_date = friendly_upload_date(info.get("upload_date") or info.get("timestamp"))
		self.channel_name = info.get("channel") or info.get("uploader") or ""
		self.channel_url = info.get("channel_url") or info.get("uploader_url") or ""

	def get_resolution(self, data):
		width = data.get("width")
		height = data.get("height")
		if width and height:
			return f"{width}x{height}"
		return data.get("resolution", "")


class YtdlpComments:
	def __init__(self, comments):
		self.comments = {"result": [self.normalize(comment) for comment in comments]}
		self.hasMoreComments = False

	def normalize(self, comment):
		author = comment.get("author") or comment.get("author_id") or _("unknown")
		if isinstance(author, dict):
			author = author.get("name") or _("unknown")
		return {
			"content": comment.get("text") or comment.get("content") or "",
			"author": {"name": author},
		}

	def getNextComments(self):
		return None


def extract_youtube_info(url):
	try:
		logger.info("Extracting YouTube info with cookies. url=%s", url)
		return extract_youtube_info_with_options(url, use_cookies=True)
	except youtube_dl.utils.DownloadError as e:
		if not is_browser_cookie_error(e):
			logger.exception("Failed to extract YouTube info. url=%s", url)
			raise
		logger.warning("Cookie-based YouTube info extraction failed; retrying without cookies. url=%s error=%s", url, e)
		return extract_youtube_info_with_options(url, use_cookies=False)


def extract_youtube_info_with_options(url, use_cookies=True):
	options = {
		"quiet": True,
		"no_warnings": True,
		"noplaylist": True,
		"skip_download": True,
	}
	options.update(get_yt_dlp_options(use_cookies=use_cookies))
	with youtube_dl.YoutubeDL(options) as ydl:
		info = ydl.extract_info(url, download=False)
	return get_first_video_info(info)


def extract_youtube_comments(url):
	try:
		logger.info("Extracting YouTube comments with cookies. url=%s", url)
		return extract_youtube_comments_with_options(url, use_cookies=True)
	except youtube_dl.utils.DownloadError as e:
		if not is_browser_cookie_error(e):
			logger.exception("Failed to extract YouTube comments. url=%s", url)
			raise
		logger.warning("Cookie-based YouTube comments extraction failed; retrying without cookies. url=%s error=%s", url, e)
		return extract_youtube_comments_with_options(url, use_cookies=False)


def extract_youtube_comments_with_options(url, use_cookies=True):
	options = {
		"quiet": True,
		"no_warnings": True,
		"noplaylist": True,
		"skip_download": True,
		"getcomments": True,
		"extractor_args": {"youtube": {"max_comments": ["30"]}},
	}
	options.update(get_yt_dlp_options(use_cookies=use_cookies))
	with youtube_dl.YoutubeDL(options) as ydl:
		info = ydl.extract_info(url, download=False)
	info = get_first_video_info(info)
	comments = info.get("comments") or []
	if not comments:
		raise youtube_dl.utils.DownloadError("No comments found")
	logger.info("Loaded %s comments. url=%s", len(comments), url)
	return YtdlpComments(comments)


def get_first_video_info(info):
	entries = info.get("entries")
	if entries:
		for entry in entries:
			if entry:
				return entry
	return info


def get_formats(info):
	formats = [format for format in info.get("formats", []) if format.get("url")]
	if info.get("url"):
		formats.append(info)
	return formats


def has_audio(format):
	return format.get("acodec") not in (None, "none")


def has_video(format):
	return format.get("vcodec") not in (None, "none")


def is_direct_media(format):
	return format.get("protocol") in (None, "http", "https")


def format_size(format):
	return format.get("filesize") or format.get("filesize_approx") or 0


def format_bitrate(format):
	return format.get("tbr") or format.get("abr") or 0


def get_format_quality(format):
	height = format.get("height")
	if height:
		return f"{height}p"
	abr = format.get("abr")
	if abr:
		return f"{abr}kbps"
	return format.get("format_note") or format.get("quality") or ""


def get_format_debug_description(format):
	parts = [
		f"format_id={format.get('format_id', '')}",
		f"ext={format.get('ext', '')}",
		f"quality={get_format_quality(format)}",
		f"resolution={format.get('resolution') or ''}",
		f"width={format.get('width') or ''}",
		f"height={format.get('height') or ''}",
		f"abr={format.get('abr') or ''}",
		f"tbr={format.get('tbr') or ''}",
		f"acodec={format.get('acodec') or ''}",
		f"vcodec={format.get('vcodec') or ''}",
		f"filesize={format_size(format) or ''}",
		f"protocol={format.get('protocol') or ''}",
	]
	return ", ".join(parts)


def is_preferred_audio_codec(format):
	extension = format.get("ext")
	codec = (format.get("acodec") or "").lower()
	return (
		extension == "m4a" and codec.startswith("mp4a")
	) or (
		extension == "webm" and "opus" in codec
	)


def audio_format_id_rank(format):
	format_id = str(format.get("format_id", ""))
	try:
		return preferred_audio_format_ids.index(format_id)
	except ValueError:
		return len(preferred_audio_format_ids)


def video_sort_key(format):
	height = format.get("height") or 0
	if height <= target_video_height:
		height_rank = target_video_height - height
	else:
		height_rank = height - target_video_height + target_video_height
	return (
		height > target_video_height,
		height_rank,
		0 if format.get("ext") == "mp4" else 1,
		format_size(format) or format_bitrate(format),
	)


def audio_sort_key(format):
	format_id = str(format.get("format_id", ""))
	bitrate = format.get("abr") or format.get("tbr") or known_audio_bitrates.get(format_id) or target_audio_bitrate
	if min_audio_bitrate <= bitrate <= max_audio_bitrate:
		bitrate_rank = 0
		bitrate_distance = abs(target_audio_bitrate - bitrate)
	elif max_audio_bitrate < bitrate <= heavy_audio_bitrate:
		bitrate_rank = 1
		bitrate_distance = bitrate - max_audio_bitrate
	elif bitrate < min_audio_bitrate:
		bitrate_rank = 2
		bitrate_distance = min_audio_bitrate - bitrate
	else:
		bitrate_rank = 3
		bitrate_distance = bitrate - heavy_audio_bitrate
	extension = format.get("ext")
	codec = (format.get("acodec") or "").lower()
	if extension == "webm" and "opus" in codec:
		codec_rank = 0
	elif extension == "m4a" and codec.startswith("mp4a"):
		codec_rank = 1
	else:
		codec_rank = 2
	return (
		codec_rank,
		bitrate_rank,
		bitrate_distance,
		audio_format_id_rank(format),
		format_size(format) or bitrate,
	)


def stream_from_format(info, format):
	stream = YtdlpStream(info.get("title", ""), format, info)
	logger.info("Media player selected format. title=%s %s", stream.title, stream.debug_description)
	return stream


def get_audio_stream(url):
	logger.info("Selecting audio stream. url=%s", url)
	info = extract_youtube_info(url)
	candidates = [
		format for format in get_formats(info)
		if has_audio(format) and not has_video(format) and is_direct_media(format)
	]
	logger.info("Found %s audio stream candidates. url=%s", len(candidates), url)
	if not candidates:
		logger.error("No audio stream found. url=%s", url)
		raise youtube_dl.utils.DownloadError("No audio stream found")
	preferred_candidates = [format for format in candidates if is_preferred_audio_codec(format)]
	if preferred_candidates:
		candidates = preferred_candidates
	return stream_from_format(info, min(candidates, key=audio_sort_key))

def get_video_stream(url):
	logger.info("Selecting video stream. url=%s", url)
	info = extract_youtube_info(url)
	candidates = [
		format for format in get_formats(info)
		if has_audio(format) and has_video(format) and is_direct_media(format)
	]
	logger.info("Found %s video stream candidates. url=%s", len(candidates), url)
	if not candidates:
		logger.error("No video stream with audio found. url=%s", url)
		raise youtube_dl.utils.DownloadError("No video stream with audio found")
	return stream_from_format(info, min(candidates, key=video_sort_key))

def time_formatting( t):
	t = t.split(":")
	t = [int(i) for i in t]
	t.pop(0) if t[0] == 0 else None
	def minute(m):
		if m == 1:
			return _("1 minute")
		elif m == 2:
			return _("2 minutes")
		elif m >=3 and m <=10:
			return _("{} minutes").format(m)
		else:
			return _("{} minutes").format(m)
	def second(s):
		if s == 1:
			return _("1 second")
		elif s == 2:
			return _("2 seconds")
		elif s >= 3 and s <= 10:
			return _("{} seconds").format(s)
		else:
			return _("{} seconds").format(s)
	def hour(h):
		if h == 1:
			return _("1 hour")
		elif h == 2:
			return _("2 hours")
		elif h >= 3 and h <=10:
			return _("{} hours").format(h)
		else:
			return _("{} hours").format(h)
	if len(t) == 1:
		return second(t[0])
	elif len(t) == 2:
		return _("{} and {}").format(minute(t[0]), second(t[1]))
	elif len(t) == 3:
		return _("{}, {} and {}").format(hour(t[0]), minute(t[1]), second(t[2]))

def youtube_regexp(string):
	pattern = re.compile("^((?:https?:)?\/\/)?((?:www|m)\.)?((?:youtube\.com|youtu.be))(\/(?:[\w\-]+\?v=|embed\/|v\/)?)([\w\-]+)(\S+)?$") # youtube links regular expression pattern
	return pattern.search(string)

def direct_download(option, url, dlg, download_type="video", path=config_get("path")):
	logger.info("Direct download requested. option=%s type=%s path=%s url=%s", option, download_type, path, url)
	if option == 0:
		format = "bestvideo[ext=mp4]+bestaudio[ext=m4a]/mp4"
	else:
		format = "bestaudio[ext=m4a]"
	convert = True if option == 2 else False
	folder = False if download_type == "video" else True
	trd = Thread(target=downloadAction, args=[url, path, dlg, format, dlg.gaugeProgress, dlg.textProgress, convert, folder])
	trd.start()

def check_for_updates(quiet=False):
	url = "https://raw.githubusercontent.com/sulaiman-alqusaimi/accessible_youtube_downloader_pro/master/update_info.json"
	try:
		logger.info("Checking for updates. quiet=%s", quiet)
		r = requests.get(url)
		if r.status_code != 200:
			logger.error("Update check failed. status=%s url=%s", r.status_code, url)
			wx.MessageBox(
				_("can not initiate a successful connection with the update service. make sure that you have a stable internet connection and try again."), 
				_("error"), 
				parent=wx.GetApp().GetTopWindow(), style=wx.ICON_ERROR
			) if not quiet else None
			return
		info = r.json()
		if application.version != info["version"]:
			logger.info("Update available. current=%s latest=%s url=%s", application.version, info["version"], info["url"])
			message = wx.MessageBox(_("there is a new available update. would you like to download it?"), _("new update"), parent=wx.GetApp().GetTopWindow(), style=wx.YES_NO)
			url = info["url"]
			if message == wx.YES:
				from gui.update_dialog import UpdateDialog
				wx.CallAfter(UpdateDialog, wx.GetApp().GetTopWindow(), url)
			return
		logger.info("No update available. version=%s", application.version)
		wx.MessageBox(_("you are running now on the latest version of the application"), _("no update"), parent=wx.GetApp().GetTopWindow()) if not quiet else None
	except requests.ConnectionError:
		logger.exception("Update check connection error. url=%s", url)
		wx.MessageBox(
			_("can not initiate a successful connection with the update service. make sure that you have a stable internet connection and try again."), 
			_("error"), 
			parent=wx.GetApp().GetTopWindow(), style=wx.ICON_ERROR
		) if not quiet else None
