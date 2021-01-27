import ctypes

dll = ".\\nvdaControllerClient32.dll"
def speak(msg):
	nvda = ctypes.windll.LoadLibrary(dll)
	running = nvda.nvdaController_testIfRunning()
	if running != 1:
		nvda.nvdaController_speakText(msg)
