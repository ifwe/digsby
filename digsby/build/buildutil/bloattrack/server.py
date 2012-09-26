import web
import bloattrack

urls = (
    '/(.*?)/(.*)', 'bloatserver'
)
app = web.application(urls, globals())
render = web.template.render('templates/')

class bloatserver(object):
    def GET(self, view, url):
        url = 'http://mini/svn/' + url
        query = web.input(rev=None)

        if view == 'treemapjson':
            web.header('Content-Type', 'text/json')
            return bloattrack.json_for_svn_url(url=url, rev=query.rev)['json']

        elif view == 'treemap':
            info = bloattrack.json_for_svn_url(url=url, rev=query.rev)
            return render.treemap(url, info['rev'], info['json'])
        else:
            return web.notfound()
            #return 'your url is wack: %r' % url

if __name__ == "__main__":
    app.run()

