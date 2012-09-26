import wx, wx.webview

app = wx.PySimpleApp()
f = wx.Frame(None, size = (640, 480))

f.Sizer = s = wx.BoxSizer(wx.VERTICAL)

b = wx.webview.WebView(f)
b.SetPageSource('''\
<html>
<head>
<link rel="stylesheet" type="text/css" href="test.css" />
</head>

<body>
<p>link to http://: <a href="http://www.yahoo.com">Yahoo!</a></p>
<p>link to local file: <a
href="file:///c:/Python24/News.txt">test.html</a></p>
<p id="wut">image stored locally: <img src="bicon.gif"></p>
</body></html>
''', "file:///c:/")
f.Show()


b.RunScript('document.getElementById("wut").style.font.weight = "normal";')

app.MainLoop()