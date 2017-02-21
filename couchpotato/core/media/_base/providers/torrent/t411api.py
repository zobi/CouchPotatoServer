from couchpotato.core.helpers.variable import tryInt
from couchpotato.core.logger import CPLog
from couchpotato.core.helpers.encoding import simplifyString, tryUrlencode
from couchpotato.core.media._base.providers.torrent.base import TorrentProvider
from couchpotato.core.helpers import namer_check
import json
import re
import unicodedata

log = CPLog(__name__)


class Base(TorrentProvider):

    urls = {
        'test': 'https://www.t411.li/',
        'torrent': 'https://www.t411.li/torrents/%s',
        'login': 'https://api.t411.li/auth',
        'detail': 'https://www.t411.li/torrents/?id=%s',
        'search': 'https://api.t411.li/torrents/search/%s',
        'download': 'https://api.t411.li/torrents/download/%s',
    }

    http_time_between_calls = 1 #seconds
    auth_token = ''

    def _search(self, movie, quality, results):
        headers = {}
        headers['Authorization'] = self.auth_token

        for title in movie['info']['titles']:
           try:
                TitleStringReal = str(title.encode("latin-1").replace('-',' '))

                url = self.urls['search'] % TitleStringReal
                url = url + '?cat=631&limit=100'
                data = self.getJsonData(url, None, headers = headers)

                for currentresult in data['torrents']:
                    if currentresult['categoryname'] in ['Film', 'Animation']:
                        name = currentresult['name']
                        splittedReleaseName = re.split('(?:\(|\.|\s)([0-9]{4})(?:\)|\.|\s)', name, flags=re.IGNORECASE)

                        if len(splittedReleaseName) > 1:
                            cleanedReleaseName = ''.join(splittedReleaseName[0:-2])

                            match = re.compile(ur"[\w]+", re.UNICODE)
                            nameSplit = ''.join(match.findall(unicodedata.normalize('NFKD', cleanedReleaseName.upper()).encode('ASCII','ignore')))
                            titleSplit = ''.join(match.findall(unicodedata.normalize('NFKD', title.upper()).encode('ASCII','ignore')))

                            if titleSplit == nameSplit:
                                new = {}
                                new['id'] = currentresult['id']
                                new['name'] = name
                                new['url'] =  self.urls['download'] % (currentresult['id'])
                                new['detail_url'] = self.urls['torrent'] % (currentresult['rewritename'])
                                new['size'] = tryInt(currentresult['size']) / 1024 / 1024
                                new['seeders'] = tryInt(currentresult['seeders'])
                                new['leechers'] = tryInt(currentresult['leechers'])
                                new['authtoken'] = self.auth_token
                                new['download'] = self.loginDownload

                                results.append(new)
           except:
                continue

        return

    def getLoginParams(self):
        return {
            'username': self.conf('username'),
            'password': self.conf('password')
        }

    def loginSuccess(self, output):
        try:
            jsonData = json.loads(output)
            if jsonData.get('uid', '') != '':
                self.auth_token = jsonData.get('token', '')
                return True
        except:
            pass

        return False

    loginCheckSuccess = loginSuccess

    def loginDownload(self, url = '', nzb_id = ''):
        try:
            if not self.login():
                log.error('Failed downloading from %s', self.getName())

            headers = {}
            headers['Authorization'] = self.auth_token
            return self.urlopen(url, None, headers = headers)
        except:
            log.error('Failed downloading from %s: %s', (self.getName(), traceback.format_exc()))

config = [{
    'name': 't411api',
    'groups': [
        {
            'tab': 'searcher',
            'list': 'torrent_providers',
            'name': 't411 api version',
            'description': 'See <a href="https://www.t411.li/">T411</a>',
            'icon' : 'iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAIAAACQkWg2AAAAA3NCSVQICAjb4U/gAAACdklEQVQokW2RX0hTcRTHz+/+cbvz3m1srbv8M6Ws6SbK1hRTkUoKIui5jIJ8sz9vQQTRQxDRexCkIGgmSC+B1YNWNCIrRQ3Z2PyTf5pb2/S2ud2/2723hyIt/b4cDud7+H4OB2CXrpOW+wYLYPju0R66DTABEAWYB7i6lwHtbEYAKi5crPE36Wa6QGKQyYylk1cePPwX4FqPquSSiZVHAN+Gh/JihpezUpGXinmxkBN5Lvjm5U4/1hzwS5JsJIkzkWnmZDtSZF2WQZZ0SSoIgiSJXq+37VjLNhLL7h/ofUzg0Dceutl1ejHOoa0fScUQW1rouXQWw3ANULXbt8cNJ7pudPrcd/pmLp8PBNpa344HDYTqYc2Ls58G+59sI/0uTgBTKj78OQIdTb6W5gKg+PpKaPprUoLB/mBHY/v/CacARru7ucaG6NCrj5vp2rpDWvmBDa83PzDwdJVOl5Zo8S+JQhoD7E/CGMBEKLyYTNWjLKNl6KkP5OsXbE1leGqdNFoBd3K034jbcJzYfqfPTpUZjOHkmkmS+SpzinXYlxdGM+4I5ezkoyHSUcIjHXHY3wWPqM9SOg2ataFMlvQ6YWs5FIvaKxxgmzEfrWYOazanXuAxAGBwGALoNcWePxtx8cKR4wGuBFZo05TI2gXViE3SaiyVn3bQRgU0DABuVdHn7na6iuSMAOk2X6WnrqLcMVlqTVQ5lHw2VaQURtNN+7YoD7L4cQCQKGo9GJsUEGC6bNPfzc1xpZAjWuH7+3u+xHy+BuFLLkYsx7la0yrCAeqdZg0h1kDQFkpVlSyvrG1krM5mNbtK/9wM0wddjF6UNywElpWVX6HUDxDMdBkmAAAAAElFTkSuQmCC',
            'wizard': True,
            'options': [
                {
                    'name': 'enabled',
                    'type': 'enabler',
                    'default': False,
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
                    'default': 0,
                    'description': 'Starting score for each release found via this provider.',
                }
            ],
        },
    ],
}]
