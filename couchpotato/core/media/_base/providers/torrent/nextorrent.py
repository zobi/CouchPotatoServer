from bs4 import BeautifulSoup
from couchpotato.core.helpers.variable import getTitle, tryInt
from couchpotato.core.logger import CPLog
from couchpotato.core.helpers.encoding import simplifyString, tryUrlencode
from couchpotato.core.media._base.providers.torrent.base import TorrentProvider
import cookielib
import re
import traceback
import urllib
import urllib2
import ssl
import unicodedata
from couchpotato.core.helpers import namer_check
from StringIO import StringIO
import gzip
log = CPLog(__name__)


class Base(TorrentProvider):

    urls = {
        'test': 'https://www.nextorrent.net',
        'search': 'https://www.nextorrent.net/torrents/recherche/',
    }

    http_time_between_calls = 1 #seconds
    cat_backup_id = None
    cj = cookielib.CookieJar()
    opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cj))

    class NotLoggedInHTTPError(urllib2.HTTPError):
        def __init__(self, url, code, msg, headers, fp):
            urllib2.HTTPError.__init__(self, url, code, msg, headers, fp)

    class PTPHTTPRedirectHandler(urllib2.HTTPRedirectHandler):
        def http_error_302(self, req, fp, code, msg, headers):
            log.debug("302 detected; redirected to %s" % headers['Location'])
            if (headers['Location'] != 'login.php'):
                return urllib2.HTTPRedirectHandler.http_error_302(self, req, fp, code, msg, headers)
            else:
                raise Base.NotLoggedInHTTPError(req.get_full_url(), code, msg, headers, fp)

    def _search(self, movie, quality, results):

                # Cookie login
        if not self.last_login_check and not self.login():
            return


        TitleStringReal = (getTitle(movie['info']) + ' ' + simplifyString(quality['identifier'] )).replace('-',' ').replace(' ',' ').replace(' ',' ').replace(' ',' ').encode("utf8")

        URL = (self.urls['search']).encode('UTF8')
        URL=unicodedata.normalize('NFD',unicode(URL,"utf8","replace"))
        URL=URL.encode('ascii','ignore')


        URL = urllib2.quote(URL.encode('utf8'), ":/?=")
        URL = URL + TitleStringReal
        values = { }
        URLTST = (self.urls['test']).encode('UTF8')

        data_tmp = urllib.urlencode(values)


        req = urllib2.Request(URL, data_tmp, headers={'User-Agent' : "Mozilla/5.0"} )

        data = urllib2.urlopen(req)

        id = 1000

        if data:

            try:
                html = BeautifulSoup(data)
                erlin=0
                resultdiv=[]
                while erlin==0:
                    try:
                        resultContent = html.findAll(attrs={'class': ["listing-torrent"]})[0]
                        if resultContent:
                            resultlin = resultContent.findAll(attrs={'class': ['table-hover']})[0].find('tbody')
                            if resultlin:
                                    trList= resultlin.findAll("tr");
                                    for tr in trList:
                                        resultdiv.append(tr)
                        erlin=1
                    except:
                        erlin=1
                nbrResult = 0
                for result in resultdiv:

                    try:
                        new = {}
                        firstTd = result.findAll("td")[0]
                        nothing = firstTd.findAll("center")
                        if nothing:
                            continue
                        name = firstTd.findAll("a")[1]['title'];
                        testname = namer_check.correctName(name,movie)
                        if testname == 0 and nbrResult < 5:
                            values_sec = {}
                            url_sec = result.findAll("a")[1]['href'];
                            req_sec = urllib2.Request(URLTST+url_sec, values_sec, headers={'User-Agent': "Mozilla/5.0"})
                            data_sec = urllib2.urlopen(req_sec)
                            if data_sec:
                                html_sec = BeautifulSoup(data_sec)
                                classlin_sec = 'torrentsdesc'
                                resultlin_sec = html_sec.findAll(attrs={'id': [classlin_sec]})[0]
                                name = resultlin_sec.find("div").text
                                name = name.replace(".", " ")
                                testname = namer_check.correctName(name, movie)
                        if testname == 0:
                            continue
                        nbrResult += 1
                        values_sec = {}
                        detail_url = result.findAll("a")[1]['href'];
                        req_sec = urllib2.Request(URLTST+detail_url, values_sec, headers={'User-Agent': "Mozilla/5.0"})
                        data_sec = urllib2.urlopen(req_sec)
                        html_sec = BeautifulSoup(data_sec)
                        classlin_sec = 'download'
                        resultlin_sec = html_sec.findAll(attrs={'class': [classlin_sec]})[0]
                        url_download = resultlin_sec.findAll("a")[0]['href']
                        size = result.findAll("td")[1].text
                        seeder = result.findAll("td")[2].text
                        leecher = result.findAll("td")[3].text
                        age = '1'

                        verify = getTitle(movie['info']).split(' ')

                        add = 1

                        for verify_unit in verify:
                            if (name.lower().find(verify_unit.lower()) == -1) :
                                add = 0

                        def extra_check(item):
                            return True

                        if add == 1:

                            new['id'] = id
                            new['name'] = name.strip() + ' french'
                            new['url'] = url_download
                            new['detail_url'] = detail_url
                            new['size'] = self.parseSize(size)
                            new['age'] = 10
                            new['seeders'] = tryInt(seeder)
                            new['leechers'] = tryInt(leecher)
                            new['extra_check'] = extra_check
                            new['download'] = self.loginDownload

                            #new['score'] = fireEvent('score.calculate', new, movie, single = True)

                            #log.error('score')
                            #log.error(new['score'])

                            results.append(new)

                            id = id+1


                    except:
                        log.error('Failed parsing zetorrents: %s', traceback.format_exc())

            except AttributeError:
                log.debug('No search results found.')
        else:
            log.debug('No search results found.')

    def ageToDays(self, age_str):
        age = 0
        age_str = age_str.replace('&nbsp;', ' ')

        regex = '(\d*.?\d+).(sec|heure|jour|semaine|mois|ans)+'
        matches = re.findall(regex, age_str)
        for match in matches:
            nr, size = match
            mult = 1
            if size == 'semaine':
                mult = 7
            elif size == 'mois':
                mult = 30.5
            elif size == 'ans':
                mult = 365

            age += tryInt(nr) * mult

        return tryInt(age)

    def login(self):
        return True



    def loginDownload(self, url = '', nzb_id = ''):
        try:
            URLTST = (self.urls['test']).encode('UTF8')
            request_headers = {
                'User-Agent': 'Mozilla/5.0',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'fr,fr-FR;q=0.8,en-US;q=0.5,en;q=0.3',
                'Accept-Encoding': 'gzip, deflate, br',
                'Referer': 'https://www.nextorrent.net/torrent/3183/beaut-cache',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1'
            }
            request = urllib2.Request(URLTST+url, headers=request_headers)
            response = self.opener.open(request)
            if response.info().get('Content-Encoding') == 'gzip':
                buf = StringIO(response.read())
                f = gzip.GzipFile(fileobj=buf)
                data = f.read()
                f.close()
            else:
                data = response.read()
            response.close()
            return data
        except:
            log.error('Failed downloading from %s: %s', (self.getName(), traceback.format_exc()))

    def download(self, url = '', nzb_id = ''):

        if not self.last_login_check and not self.login():
            return

        values = {
          'url' : '/'
        }
        data_tmp = urllib.urlencode(values)
        req = urllib2.Request(url, data_tmp, headers={'User-Agent' : "Mozilla/5.0"} )

        try:
            return urllib2.urlopen(req).read()
        except:
            log.error('Failed downloading from %s: %s', (self.getName(), traceback.format_exc()))
config = [{
    'name': 'nextorrent',
    'groups': [
        {
            'tab': 'searcher',
            'list': 'torrent_providers',
            'name': 'nextorrent',
            'description': 'See <a href="https://www.nextorrent.com/">nextorrent</a>',
            'icon': 'iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAAACXBIWXMAAAsTAAALEwEAmpwYAAAAIGNIUk0AAHolAACAgwAA+f8AAIDpAAB1MAAA6mAAADqYAAAXb5JfxUYAAAI5SURBVHjabJM/T+NAEMV/u57YsQ05pBS00EQiJFKIoOGTUFFDQY0QfAFo4FNQI0FDg+iogPTuafJHCiaOUbzra7DPubuVRlqtZt68eW9W+b7/sbGxsaK1BsBaS5ZlKKXKyPO8vBd5P7lforX+1ev1gna7XQIMBgPe398REUQEpRRpmrK1tcXu7i6e55FlGa+vr444jmP29vY4ODjAGEOtViOKIm5ubnh5eSEIAkSE7+9vWq0Wh4eHrK6ukiQJs9nM6CrtxWLBfD6n1WpxcnJCv99nNpthjEEpVeYVYa3lz0A/J89zkiSh0+lwenpKv98njmOMMfzv6DzPl4q11ogIcRzT6XQ4Ozuj2+0ynU5LkGqNLlQuipMkIY5jgiBgMpnQ7XY5Pz+n3W7z+fmJMWbJCV21yPM8hsMht7e3RFFEs9lkNBrR6/W4uLhgZ2cHYwzW2hJAqpQcx8FxHJ6enhgMBlxdXbG+vs54PGZ/f5/t7W2UUkt6aAClVDmbiNBoNHh+fuby8pLhcMja2hrz+Rzf96nVav9q8LcLIkIYhjw+PnJ9fc1oNCIMQ7IsK/UqGkv1ocrG8zwcx+H+/p56vc7x8TGNRoM0TZcZK6UQETzPK0NrjbWWMAwBuLu7Q2vN0dERzWaTxWJR6iXWWt7e3siyDBFhMpkwHo9xXZc8z6nX66RpysPDQ7mlhRNRFKF8359tbm4Ghbd5ni8tTEG36Oq6bvU3Jsp13Q+l1EpVmOqiFCCFVksOaP31ewAjgDxHOfDVqAAAAABJRU5ErkJggg==',
            'wizard': True,
            'options': [
                {
                    'name': 'enabled',
                    'type': 'enabler',
                    'default': False,
                },
                        {
                    'name': 'seed_ratio',
                    'label': 'Seed ratio',
                    'type': 'float',
                    'default': 1,
                    'description': 'Will not be (re)moved until this seed ratio is met.',
                },
                {
                    'name': 'seed_time',
                    'label': 'Seed time',
                    'type': 'int',
                    'default': 40,
                    'description': 'Will not be (re)moved until this seed time (in hours) is met.',
                },
                {
                    'name': 'extra_score',
                    'advanced': True,
                    'label': 'Extra Score',
                    'type': 'int',
                    'default': 0,
                    'description': 'Starting score for each release found via this provider.',
                }
            ],
        },
    ],
}]
