import os
import re
import sys

import requests

from app_logger import get_logger
from paths import yt_dlp_component_path


logger = get_logger()
PYPI_JSON_URL = "https://pypi.org/pypi/yt-dlp/json"
WHEEL_PATTERN = re.compile(r"yt_dlp-(?P<version>[^-]+)-py3-none-any\.whl$")


def parse_version(version):
	parts = []
	for part in str(version).replace("_", ".").replace("-", ".").split("."):
		try:
			parts.append(int(part))
		except ValueError:
			parts.append(part)
	return tuple(parts)


def component_wheels():
	if not os.path.isdir(yt_dlp_component_path):
		return []
	wheels = []
	for name in os.listdir(yt_dlp_component_path):
		match = WHEEL_PATTERN.match(name)
		if match is not None:
			wheels.append((parse_version(match.group("version")), os.path.join(yt_dlp_component_path, name)))
	return sorted(wheels, reverse=True)


def activate_ytdlp_component():
	wheels = component_wheels()
	if not wheels:
		return
	wheel_path = wheels[0][1]
	if wheel_path not in sys.path:
		sys.path.insert(0, wheel_path)
	logger.info("Using yt-dlp component wheel: %s", wheel_path)


def get_active_ytdlp_version():
	import yt_dlp.version
	return yt_dlp.version.__version__


def latest_wheel_info():
	logger.info("Checking latest yt-dlp component version")
	response = requests.get(PYPI_JSON_URL, timeout=20)
	response.raise_for_status()
	data = response.json()
	version = data["info"]["version"]
	for file_info in data["releases"].get(version, []):
		if file_info.get("packagetype") == "bdist_wheel" and file_info.get("filename", "").endswith("py3-none-any.whl"):
			return {
				"version": version,
				"filename": file_info["filename"],
				"url": file_info["url"],
			}
	raise RuntimeError("No compatible yt-dlp wheel found")


def is_newer_version(version, current_version):
	return parse_version(version) > parse_version(current_version)


def install_ytdlp_component_update():
	try:
		current_version = get_active_ytdlp_version()
		latest = latest_wheel_info()
		if not is_newer_version(latest["version"], current_version):
			logger.info("yt-dlp component is already current. current=%s latest=%s", current_version, latest["version"])
			return {"updated": False, "version": current_version}
		os.makedirs(yt_dlp_component_path, exist_ok=True)
		final_path = os.path.join(yt_dlp_component_path, latest["filename"])
		if not os.path.exists(final_path):
			temp_path = f"{final_path}.tmp"
			logger.info("Downloading yt-dlp component update. current=%s latest=%s", current_version, latest["version"])
			with requests.get(latest["url"], stream=True, timeout=60) as response:
				response.raise_for_status()
				with open(temp_path, "wb") as file:
					for part in response.iter_content(1024 * 64):
						if part:
							file.write(part)
			os.replace(temp_path, final_path)
		cleanup_old_wheels(final_path)
		logger.info("yt-dlp component update installed. version=%s path=%s", latest["version"], final_path)
		return {"updated": True, "version": latest["version"], "path": final_path}
	except Exception as e:
		logger.exception("Could not update yt-dlp component")
		return {"updated": False, "error": str(e)}


def cleanup_old_wheels(keep_path):
	for _, wheel_path in component_wheels():
		if os.path.abspath(wheel_path) == os.path.abspath(keep_path):
			continue
		try:
			os.remove(wheel_path)
		except OSError:
			logger.exception("Could not remove old yt-dlp component wheel: %s", wheel_path)
