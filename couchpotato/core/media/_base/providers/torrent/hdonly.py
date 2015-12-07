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


log = CPLog(__name__)


class Base(TorrentProvider):

    urls = {
        'domain': 'https://hd-only.org',
        'detail': 'https://hd-only.org/torrents.php?torrentid=%s',
        'torrent': 'https://hd-only.org/torrents.php?action=download&id=%s&authkey=%s&torrent_pass=%s',
        'login': 'https://hd-only.org/login.php',
        'login_check': 'https://hd-only.org/login.php',
        'search': 'https://hd-only.org/ajax.php?action=browse&searchstr=%s',
        'index': 'https://hd-only.org/ajax.php?action=index'
    }

    http_time_between_calls = 2

    def _search(self, media, quality, results):

        indexResponse = self.getJsonData(self.urls['index'])

        authkey = indexResponse['response']['authkey']
        passkey = indexResponse['response']['passkey']

        for title in media['info']['titles']:
            try:
                TitleStringReal = str(title.encode("latin-1").replace('-',' '))
            
                url = self.urls['search'] % tryUrlencode(TitleStringReal)
                data = self.getJsonData(url)

                if data['status'] == 'success':

                    name = data['response']['results'][0]['groupName'].upper()
                    splittedReleaseName = re.split('(\.[0-9]{4}\.)', name, flags=re.IGNORECASE)
                    cleanedReleaseName = ''.join(splittedReleaseName)

                    match = re.compile(ur"[\w]+", re.UNICODE)
                    nameSplit = ''.join(match.findall(cleanedReleaseName))
                    titleSplit = ''.join(match.findall(title.upper()))

                    if titleSplit == nameSplit: # and self.matchLanguage(media['info']['languages'], re.split('[\. ]', splittedReleaseName[-1])):
                        for torrent in data['response']['results'][0]['torrents']:
                            results.append({
                                'id': torrent['torrentId'],
                                'name': name + '.' + torrent['encoding'] + '.' +  torrent['media'] + '.' +  torrent['format'],
                                'Source': torrent['media'],
                                'Resolution': torrent['encoding'],
                                'url': self.urls['torrent'] % (torrent['torrentId'], authkey, passkey),
                                'detail_url': self.urls['detail'] % torrent['torrentId'],
                                'date': tryInt(time.mktime(parse(torrent['time']).timetuple())),
                                'size': tryInt(torrent['size']) / 1024 / 1024,
                                'seeders': tryInt(torrent['seeders']),
                                'leechers': tryInt(torrent['leechers']),
                                })
            except:
                continue

    def getLoginParams(self):
        return {
            'username': self.conf('username'),
            'password': self.conf('password'),
            'keeplogged': '1',
            'login': tryUrlencode('M\'identifier')
        }

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
