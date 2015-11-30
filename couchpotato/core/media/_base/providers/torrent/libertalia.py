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
        'login' : 'https://libertalia.me/login.php',
        'detail' : 'https://libertalia.me/torrents.php?id=%s',
        'search' : 'https://libertalia.me/torrents.php?',
        'home' : 'https://libertalia.me/%s',
    }

    http_time_between_calls = 1 #seconds

    def _search(self, media, quality, results):

        #urllib.urlencode( {'name': getTitle(media['info']) })
        for title in media['info']['titles']:
            try:
                TitleStringReal = str(title.encode("latin-1").replace('-',' '))
            
                url = self.urls['search'] + urllib.urlencode( {'name':title.encode('utf-8') }) + '&cat%5B%5D=3.0&cat%5B%5D=3.1&cat%5B%5D=3.2&cat%5B%5D=3.3&cat%5B%5D=3.4&cat%5B%5D=3.5&cat%5B%5D=4.0&cat%5B%5D=4.1&cat%5B%5D=4.2&cat%5B%5D=4.3&cat%5B%5D=4.4&cat%5B%5D=4.5'
                data = self.getHTMLData(url)
        
                if data:
                  html = BeautifulSoup(data)
                  try:
                      #Get first entry in table
                      torrentTable = html.find('table', class_ = 'torrent_table')

                      if torrentTable:
                          torrents = torrentTable.find_all('tr', class_ = 'torrent_row  new  ')

                          for torrentRow in torrents:
                  
                              nameCell = torrentRow.find('td', class_ = 'torrent_name')
                              downloadCell = torrentRow.find('td', class_ = 'torrent_dl_container')
                              sizeCell = torrentRow.find('td', class_ = 'number_column nobr')
                              seedersCell = torrentRow.find_all('td', class_ = 'number_column')[1]
                              leechersCell = torrentRow.find_all('td', class_ = 'number_column')[2]

                              name = nameCell.find_all('a')[1].get_text().upper()

                              splittedReleaseName = re.split('( [0-9]{4} )', name, flags=re.IGNORECASE)

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
                                      new['url'] = downloadUrl
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
    'name': 'libertalia',
    'groups': [
        {
            'tab': 'searcher',
            'list': 'torrent_providers',
            'name': 'libertalia',
            'description': 'See <a href="https://libertalia.me">Libertalia</a>',
            'wizard': True,
            'icon': 'iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAIAAACQkWg2AAAACXBIWXMAAAsTAAALEwEAmpwYAAABJ0lEQVR4nGNMjI1hIAUwkaSaLA1S0jKmZmaMjIxEamBWVVI0NDYODg39+ePn2zdv/v79S0CDgZ7e7Vu3vn37FhQSampm/v///yePH////x9NnZCwsJiY+MePH5gN9fUYGBieP3t29OgRLS0tDy8vVlbW69euQtSxc3CYm1vo6uuzs7Nfu3aVgYEBqoGBgeHPnz/Xr13V09dXUVO7cf36xw8feHh4QsLCnj19eub0qYcPHkCdBNfAwMDw69ev+/fumVtYWlpZ/fr12zfAf/WKFffu3f3z+zcilNDc+vDBg1XLl/Pw8kbHxj598uQ3klIIYEHjS0pJObu5Xb927cGD+1s2bvr16yeaAkbMpMHBwfHz50/MgMJuAwMDw48fP7Aqxe4HgoD2GgBqlXZsCEwcWgAAAABJRU5ErkJggg==',
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