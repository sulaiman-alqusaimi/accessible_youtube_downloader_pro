import logging
import os
import sys
from logging.handlers import RotatingFileHandler

from paths import settings_path


log_path = os.path.join(settings_path, "accessible_youtube_downloader_pro.log")
logger = logging.getLogger("accessible_youtube_downloader_pro")
_exception_hooks_installed = False


def setup_logging():
	os.makedirs(settings_path, exist_ok=True)
	if logger.handlers:
		return logger
	logger.setLevel(logging.DEBUG)
	logger.propagate = False
	file_handler = RotatingFileHandler(log_path, maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8")
	file_handler.setLevel(logging.DEBUG)
	file_handler.setFormatter(logging.Formatter(
		"%(asctime)s \n%(levelname)s [%(threadName)s] %(module)s.%(funcName)s:%(lineno)d - %(message)s"
	))
	logger.addHandler(file_handler)
	logging.captureWarnings(True)
	logger.info("Logging initialized: %s", log_path)
	return logger


def get_logger():
	if not logger.handlers:
		setup_logging()
	return logger


def install_exception_logging():
	global _exception_hooks_installed
	if _exception_hooks_installed:
		return
	_exception_hooks_installed = True
	setup_logging()
	original_excepthook = sys.excepthook

	def log_unhandled_exception(exc_type, exc_value, exc_traceback):
		if issubclass(exc_type, KeyboardInterrupt):
			return original_excepthook(exc_type, exc_value, exc_traceback)
		logger.exception("Unhandled exception", exc_info=(exc_type, exc_value, exc_traceback))
		return original_excepthook(exc_type, exc_value, exc_traceback)

	sys.excepthook = log_unhandled_exception

	if hasattr(sys, "unraisablehook"):
		original_unraisablehook = sys.unraisablehook

		def log_unraisable_exception(unraisable):
			logger.error(
				"Unraisable exception in %r: %s",
				unraisable.object,
				unraisable.err_msg,
				exc_info=(unraisable.exc_type, unraisable.exc_value, unraisable.exc_traceback),
			)
			return original_unraisablehook(unraisable)

		sys.unraisablehook = log_unraisable_exception

	try:
		import threading
	except ImportError:
		return

	if hasattr(threading, "excepthook"):
		original_threading_excepthook = threading.excepthook

		def log_thread_exception(args):
			logger.exception(
				"Unhandled thread exception in %s",
				getattr(args.thread, "name", "unknown"),
				exc_info=(args.exc_type, args.exc_value, args.exc_traceback),
			)
			return original_threading_excepthook(args)

		threading.excepthook = log_thread_exception
