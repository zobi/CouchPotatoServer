import traceback
import urlparse
import urllib
import re
import unicodedata

from datetime import datetime
from bs4 import BeautifulSoup
from couchpotato.core.helpers.encoding import toUnicode, simplifyString, tryUrlencode
from couchpotato.core.helpers.variable import getTitle, tryInt
from couchpotato.core.logger import CPLog
from couchpotato.core.media._base.providers.torrent.base import TorrentProvider
import re

log = CPLog(__name__)


class Base(TorrentProvider):
    urls = {
        'login' : 'https://abnormal.ws/login.php',
        'detail' : 'https://abnormal.ws/torrents.php?id=%s',
        'search' : 'https://abnormal.ws/torrents.php?',
        'home' : 'https://abnormal.ws/%s',
    }

    http_time_between_calls = 1 #seconds

    def _search(self, media, quality, results):

        #urllib.urlencode( {'name': getTitle(media['info']) })
        for title in media['info']['titles']:
            try:
                TitleStringReal = str(title.encode("latin-1").replace('-',' '))
            
                url = self.urls['search'] + 'cat[]=MOVIE|DVDR&cat[]=MOVIE|DVDRIP&cat[]=MOVIE|BDRIP&cat[]=MOVIE|VOSTFR&cat[]=MOVIE|HD|720p&cat[]=MOVIE|HD|1080p&cat[]=MOVIE|REMUXBR&cat[]=MOVIE|FULLBR&cat[]=ANIME&' + urllib.urlencode( {'search': unicodedata.normalize('NFKD', title).encode('ASCII', 'ignore').replace('\'', ' ') }) + '&order=Time&way=desc'

                data = self.getHTMLData(url)
        
                if data:
                  html = BeautifulSoup(data)
                  try:
                      #Get first entry in table
                      torrentTable = html.find('table', class_ = 'torrent_table cats')

                      if torrentTable:
                          torrents = torrentTable.find_all('tr', class_=None)
                          torrents += torrentTable.find_all('tr', class_='tablerow-lightgrey')

                          for torrentRow in torrents:
                  
                              nameCell = torrentRow.find_all('td')[1]
                              downloadCell = torrentRow.find_all('td')[3]
                              sizeCell = torrentRow.find_all('td')[4]
                              seedersCell = torrentRow.find_all('td')[6]
                              leechersCell = torrentRow.find_all('td')[7]

                              name = nameCell.find_all('a')[0].get_text().upper()

                              splittedReleaseName = re.split('(\.[0-9]{4}\.)', name, flags=re.IGNORECASE)

                              if len(splittedReleaseName) > 1:
                                  cleanedReleaseName = ''.join(splittedReleaseName[0:-2])

                                  match = re.compile(ur"[\w]+", re.UNICODE)
                                  nameSplit = ''.join(match.findall(unicodedata.normalize('NFKD', cleanedReleaseName).encode('ASCII','ignore')))
                                  titleSplit = ''.join(match.findall(unicodedata.normalize('NFKD', title.upper()).encode('ASCII','ignore')))

                                  if titleSplit == nameSplit and self.matchLanguage(media['info']['languages'], re.split('[\. ]', splittedReleaseName[-1])):
                                      downloadUrl = downloadCell.find('a')['href']
                                      parsed = urlparse.urlparse(downloadUrl)
                                      torrent_id = urlparse.parse_qs(parsed.query)['id']

                                      new = {}
                                      new['id'] = torrent_id
                                      new['name'] = name
                                      new['url'] =  self.urls['home'] % (downloadUrl)
                                      new['detail_url'] = self.urls['home'] % (nameCell.find('a')['href'])
                                      new['size'] = self.parseSize(sizeCell.get_text())
                                      new['seeders'] = tryInt(seedersCell.get_text())
                                      new['leechers'] = tryInt(leechersCell.get_text())
                         
                                      results.append(new)
                  except:
                      log.error('Failed getting results from %s: %s', (self.getName(), traceback.format_exc()))
            except:
                continue
    
    def matchLanguage(self, languages, releaseMetaDatas):
        if self.conf('vo_only'):
            if any(l for l in languages if l.upper() in releaseMetaDatas) or 'MULTI' in releaseMetaDatas:
                return True
            else:
                return False

        return True 
   
    def getLoginParams(self):
        return {
            'username': self.conf('username'),
            'password': self.conf('password'),
            'Login': '',
        }

    def loginSuccess(self, output):
        return 'logout.php' in output.lower()

    loginCheckSuccess = loginSuccess


config = [{
    'name': 'abnormal',
    'groups': [
        {
            'tab': 'searcher',
            'list': 'torrent_providers',
            'name': 'abnormal',
            'description': 'See <a href="https://abnormal.ws">Abnormal</a>',
            'wizard': True,
            'icon': 'iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAIAAACQkWg2AAABzElEQVR4nJWQW08TURSF97nMzJlbO6XtFNuCKQzRcjFFSkCixkSCCSa++Qv9E0QTgw8+mGhqFFQQCS2lthRb6AxzKzPjgyYKosJ623vl2ytrA1xS5M8VQqh066GeM1p7WxcC8oWJq2MlgcnH5qFtdc+4+OwBQq/duI0xAYTyI1MA6D9A4XpZUjSEUBQGABAfGPwXQDmhWLoLACd9/9jsBH2vfOcRJvSvHabK99V46qBVc2xLFJXh0SLGmBDablbPSWCSakzMrVdWP1RW4wmdSbLn2kk9v7D4mDH5nITJ8uKJ76+9fuY6lqQm0pkhbSDDM1FgMiJkd3vtVIIox1J6buP9yzAMAeDrzkeeyYBQFEVRFE7PPZAU7RRwc2GZEH6/sf1j/NauN+tbURiGQeB7ruOYkzP3fgExTadUfLHy5PcHrL95bpldq9fxPZsSWppfUuPpnx0SqeFety2pWjprZHKGnh3VsyO7X94NFYpj47NKLEk5ARDieGFn8y0WmMpRHnOCHEsxUUkkB43izPT8EgBUXj3FmCKMEAACMMZnteQVwnMsCMO+7/qOyQQBYeTZ5sF+ba/6ybGOXMfqdVqN+majutGsfT46bMNl9R01bKCKBrRO8wAAAABJRU5ErkJggg==',
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
                    'default': 20,
                    'description': 'Starting score for each release found via this provider.',
                },
                {
                    'name': 'vo_only',
                    'advanced': True,
                    'label': 'Original language only',
                    'type': 'bool',
                    'default': False,
                    'description': 'Only download releases with the original language of the movie'
                }
            ],
        },
    ],
}]