import wx
import re
import webbrowser
import pyperclip


url = re.compile(r"(?i)\b((?:https?://|www\d{0,3}[.]|[a-z0-9.\-]+[.][a-z]{2,4}/)(?:[^\s()<>]+|\(([^\s()<>]+|(\([^\s()<>]+\)))*\))+(?:\(([^\s()<>]+|(\([^\s()<>]+\)))*\)|[^\s`!()\[\]{};:'\".,<>?«»“”‘’]))")

class DescriptionDialog(wx.Dialog):
	def __init__(self, parent, content):
		wx.Dialog.__init__(self, parent, title=_("وصف الفيديو"), size=(500, 500))
		self.Centre()
		self.content = content
		panel = wx.Panel(self)
		lbl = wx.StaticText(panel, -1, _("الوصف: "))
		self.contentBox = wx.TextCtrl(panel, -1, value=self.process(), style=wx.TE_PROCESS_ENTER|wx.TE_READONLY|wx.TE_MULTILINE|wx.HSCROLL)
		copyButton = wx.Button(panel, -1, _("نسخ"), name="export")
		txtExport = wx.Button(panel, -1, _("التصدير إلى مستند نصي (txt)..."), name="export")
		htmlExport = wx.Button(panel, -1, _("التصدير إلى صفحة ويب (html)..."), name="export")
		closeButton = wx.Button(panel, wx.ID_CANCEL, _("إغلاق"))
		for button in panel.GetChildren():
			button.Disable() if self.content == "" and button.Name == "export" else None
		sizer = wx.BoxSizer(wx.VERTICAL)
		sizer1 = wx.BoxSizer(wx.HORIZONTAL)
		sizer2 = wx.BoxSizer(wx.HORIZONTAL)
		sizer1.Add(lbl, 1)
		sizer1.Add(self.contentBox, 1)
		sizer2.Add(copyButton, 1)
		sizer2.Add(txtExport, 1)
		sizer2.Add(htmlExport, 1)
		sizer2.Add(closeButton, 1)
		sizer.Add(sizer1)
		sizer.Add(sizer2)
		panel.SetSizer(sizer)
		self.contentBox.Bind(wx.EVT_TEXT_ENTER, self.onOpen)
		copyButton.Bind(wx.EVT_BUTTON, self.onCopy)
		txtExport.Bind(wx.EVT_BUTTON, self.onTxt)
		htmlExport.Bind(wx.EVT_BUTTON, self.onHtml)
		closeButton.Bind(wx.EVT_BUTTON, lambda event: self.Destroy())
		self.Bind(wx.EVT_CLOSE, lambda event: self.Destroy())
		self.ShowModal()
	def process(self):
		if self.content == "":
			return self.content
		content = self.content
		if url.search(self.content) is not None:
			content = url.sub(r"\n\1", content)
		content = re.sub("\n{2,}", "\n", content)
		return content

	def onOpen(self, event):
		position = self.contentBox.PositionToXY(self.contentBox.GetInsertionPoint())
		line = self.contentBox.GetLineText(position[-1])
		match = url.search(line)
		if match is not None:
			webbrowser.open(match.group())

	def onTxt(self, event):
		path = wx.SaveFileSelector("", ".txt", parent=self)
		if path:
			with open(path, "w", encoding="utf-8") as file:
				file.write(self.content)
		self.contentBox.SetFocus()

	def onHtml(self, event):
		content = f"""<html>
<head>
<meta charset='utf-8'>
<title>{self.Parent.title}</title>
</head>
<body>
"""
		description = self.contentBox.Value.split("\n")
		for line in range(len(description)):
			match = url.search(description[line])
			if match is not None:
				description[line] = f'<a href="{match.group()}">{match.group()}</a>'
		description = "<br \>\n".join(description)
		content += f"""<h1>{self.Parent.title}</h1>
<p>{description}</p>
</body>
</html>"""
		path = wx.SaveFileSelector(" ", ".html", parent=self)
		if path:
			with open(path, "w", encoding="utf-8") as file:
				file.write(content)
		self.contentBox.SetFocus()

	def onCopy(self, event):
		pyperclip.copy(self.content)
		self.contentBox.SetFocus()