import htmlentitydefs
import json
import re
import unicodedata
import urllib
import time
import traceback

from couchpotato.core.helpers.encoding import tryUrlencode
from couchpotato.core.helpers.variable import getTitle, tryInt, mergeDicts, getIdentifier
from couchpotato.core.logger import CPLog
from couchpotato.core.media._base.providers.torrent.base import TorrentProvider
from dateutil.parser import parse
import six
from HTMLParser import HTMLParser


log = CPLog(__name__)


class Base(TorrentProvider):

    urls = {
        'domain': 'https://hd-only.org',
        'detail': 'https://hd-only.org/ajax.php?action=torrent&id=%s',
        'torrent': 'https://hd-only.org/torrents.php?action=download&id=%s&authkey=%s&torrent_pass=%s',
        'login': 'https://hd-only.org/login.php',
        'login_check': 'https://hd-only.org/login.php',
        'search': 'https://hd-only.org/ajax.php?action=browse&searchstr=%s',
        'index': 'https://hd-only.org/ajax.php?action=index'
    }

    http_time_between_calls = 2

    def _search(self, media, quality, results):

        h = HTMLParser()

        indexResponse = self.getJsonData(self.urls['index'])

        authkey = indexResponse['response']['authkey']
        passkey = indexResponse['response']['passkey']

        title = media['title']
        
        TitleStringReal = str(title.encode("latin-1").replace('-',' '))

        frTitle = self.getFrenchTitle(TitleStringReal)
        if frTitle is None:
            frTitle = TitleStringReal
            
        url = self.urls['search'] % tryUrlencode(frTitle)
        data = self.getJsonData(url)

        if data['status'] == 'success' and len(data['response']['results']) > 0:
            name = data['response']['results'][0]['groupName'].upper()
            splittedReleaseName = re.split('(\.[0-9]{4}\.)', name, flags=re.IGNORECASE)
            cleanedReleaseName = ''.join(splittedReleaseName)

            match = re.compile(ur"[\w]+", re.UNICODE)
            nameSplit = ''.join(match.findall(cleanedReleaseName))
            titleSplit = ''.join(match.findall(frTitle.upper()))

            if titleSplit == nameSplit: # and self.matchLanguage(media['info']['languages'], re.split('[\. ]', splittedReleaseName[-1])):
                for torrent in data['response']['results'][0]['torrents']:

                    detail_url = self.urls['detail'] % torrent['torrentId']
                    if not self.getJsonData(detail_url)['response']['torrent']['filePath']:
                        detail = self.getJsonData(detail_url)['response']['torrent']['fileList'].lower()
                    else:
                        detail = self.getJsonData(detail_url)['response']['torrent']['filePath'].lower()

                    detailName = h.unescape(detail)

                    results.append({
                        'id': torrent['torrentId'],
                        'name': detailName, #name + '.' + torrent['encoding'] + '.' +  torrent['media'] + '.' +  torrent['format'],
                        'Source': torrent['media'],
                        'Resolution': torrent['encoding'],
                        'url': self.urls['torrent'] % (torrent['torrentId'], authkey, passkey),
                        'detail_url': self.urls['detail'] % torrent['torrentId'],
                        'date': tryInt(time.mktime(parse(torrent['time']).timetuple())),
                        'size': tryInt(torrent['size']) / 1024 / 1024,
                        'seeders': tryInt(torrent['seeders']),
                        'leechers': tryInt(torrent['leechers']),
                        })

    def getLoginParams(self):
        return {
            'username': self.conf('username'),
            'password': self.conf('password'),
            'keeplogged': '1',
            'login': tryUrlencode('M\'identifier')
        }

    def getFrenchTitle(self, title):
        """
        This function uses TMDB API to get the French movie title of the given title.
        """

        url = "https://api.themoviedb.org/3/search/movie?api_key=0f3094295d96461eb7a672626c54574d&language=fr&query=%s" % title
        log.debug('#### Looking on TMDB for French title of : ' + title)
        #data = self.getJsonData(url, decode_from = 'utf8') 
        data = self.getJsonData(url)
        try:
            if data['results'] != None:
                for res in data['results']:
                    #frTitle = res['title'].lower().replace(':','').replace('  ',' ').replace('-','')
                    frTitle = res['title'].lower().replace(':','').replace('  ',' ')
                    if frTitle == title:
                        log.debug('#### TMDB report identical FR and original title')
                        return None
                    else:
                        log.debug(u'#### TMDB API found a french title : ' + frTitle)
                        return frTitle
            else:
                log.debug('#### TMDB could not find a movie corresponding to : ' + title)
                return None
        except:
            log.error('#### Failed to parse TMDB API: %s' % (traceback.format_exc()))


    def loginSuccess(self, output):
        return 'logout' in output.lower()

    loginCheckSuccess = loginSuccess


config = [{
    'name': 'hdonly',
    'groups': [
        {
            'tab': 'searcher',
            'list': 'torrent_providers',
            'name': 'hdonly',
            'description': '<a href="https://hd-only.org">HD-Only.org</a>',
            'wizard': True,
            'icon': 'iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAIAAACQkWg2AAACf0lEQVR4nLXSz07TYAAA8O9bW9Ztbcfc2EZEHVu3GDc6wGgwgoGTXow3jUaDIgcv+AK+g/Hgn4MX7ibuICpiUBKBAeLI5sZIgEEGhnXZGPvabmv7dfUZPPh7hh8A/xuM9cVvTz69OTY0s7ByffjScjofDvRUTyQDQF8nk98/HImf/7S4fmt06P3XxcT0a3hvfDISCWd/Z4W4kMvmQnxILIkOxgEAkGXF7/ft7OzGYtF0OiMIfbncJnz55m2xuO/xeI6rx16fFyHJ5/MqsmICwDCMKJY4jhPFstvtrlQq/m4fea6nm6Ygx3V63S6Oc2KsuzpdRtsAAHZ0UG4XRxKEy8k67PZTTtbp5MjP899binLudPfW9q6NYWkrrek6be2gafrh/bv1Ono13y8eAQBIA3J3Yi9gIpFASG62WrWTWqg3QFiI2S9z5bL4eOKRjvHct2Sq/qyn8WSgPzqzPdXltZMLP5YMjNumCQEsiWWMcWFvLz4w+OHjrNFurteeAwIPXbm8urbGMvsHB2eJIB+pVKuB3kAqldIxVlXNztjVltpQW5retjbe1eCNenFaEC78LI6SUCHCPE+R1MHhH4qiQLttGgbWsa5puqrmN3NXh0eOtcEjdWyrfBFjcEabgg/GJ5qNBklRBjZomxVCC8sypgkAMCGEkiSZptlqtkwAgGmSFGlhHA6E6nabDaET2kpLCEFgkWVJlhUIIEKS1UrXEeJYpo4Qy7CEJDdCIT6ZXA6HI6urKx5PV35rU9V0SUK7hT2OY3+lNvhQcCm5Eg7zy8kkHL42upHOxIX+TCYdjcYKhR2v168oMgCAcThK5XIoGMzmcnFBSGfSA3Hhn7f+Ba/6N2aE1SAhAAAAAElFTkSuQmCC',
            'options': [
                {
                    'name': 'enabled',
                    'type': 'enabler',
                    'default': False
                },
                {
                    'name': 'username',
                    'default': '',
                },
                {
                    'name': 'password',
                    'default': '',
                    'type': 'password',
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
                    'default': 20,
                    'description': 'Starting score for each release found via this provider.',
                }
            ],
        }
    ]
}]
