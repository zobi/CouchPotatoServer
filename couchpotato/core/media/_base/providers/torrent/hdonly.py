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
            'description': '<a href="https://hd-only.org">HD-Only.me</a>',
            'wizard': True,
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
