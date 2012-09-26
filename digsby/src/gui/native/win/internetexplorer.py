'''
a comtypes driven IE
'''

class InternetExplorer(object):
    def __init__(self):
        from comtypes.client import CreateObject, GetEvents

        self.ie = CreateObject("InternetExplorer.Application")
        self.ie.Toolbar = False
        self.ie.StatusBar = False

    def Show(self, shown = True):
        self.ie.Visible = shown

    def LoadUrl(self, url):
        self.ie.Navigate(url)

    @property
    def Cookie(self):
        return self.ie.Document.parentWindow.execScript('document.cookie')

def main():
    ie = InternetExplorer()
    ie.LoadUrl('http://www.facebook.com')
    ie.Show()

    print ie.Cookie

if __name__ == '__main__':
    main()
