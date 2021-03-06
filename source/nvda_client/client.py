import ctypes
import platform

arch = platform.architecture()[0]
dll = f".\\nvdaControllerClient{'32' if arch == '32bit' else '64'}.dll"
nvda = ctypes.windll.LoadLibrary(dll)

def speak(msg):
	running = nvda.nvdaController_testIfRunning()
	if running != 1:
		nvda.nvdaController_speakText(msg)
