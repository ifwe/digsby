import wx, wx.webview

app = wx.PySimpleApp()
f = wx.Frame(None, size = (640, 480))
b = wx.webview.WebView(f)
b.LoadURL('http://www.google.com')

# show an alert box
b.RunScript('alert("test");')

# modify some CSS
b.RunScript("document.getElementById('mydiv').style.color = '#0000ff';")

f.Show()
app.MainLoop()

