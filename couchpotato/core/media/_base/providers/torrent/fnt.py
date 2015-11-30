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
        'login' : 'https://fnt.nu/account-login.php',
        'detail' : 'https://fnt.nu/torrents.php?id=%s',
        'search' : 'https://fnt.nu/torrents/recherche/?afficher=1&',
        'home' : 'https://fnt.nu/%s',
    }

    http_time_between_calls = 1 #seconds

    def _search(self, media, quality, results):

        #urllib.urlencode( {'name': getTitle(media['info']) })
        for title in media['info']['titles']:
            try:
                TitleStringReal = str(title.encode("latin-1").replace('-',' '))
            
                url = self.urls['search'] + urllib.urlencode( {'recherche':title.encode('utf-8') }) + '&c116=1&c151=1&c100=1&c101=1&c127=1&c102=1&c103=1&c104=1&c105=1&c106=1&c107=1&c108=1&c130=1&c115=1&c128=1&c131=1&c147=1&visible=0&freeleech=0&nuke=0&3D=0&langue=0'
                data = self.getHTMLData(url)
        
                if data:
                  html = BeautifulSoup(data)
                  try:
                      torrentTable = html.find('table', attrs = {'id' : ["tablealign3bis"] })

                      if torrentTable:
                          torrents = torrentTable.find_all('tr', class_ = 'ligntorrent')

                          for torrentRow in torrents:
                              try:
                                  mediaTypeCell = torrentRow.find_all('td', class_ = 'arrondi')[0]
                                  popinCell = torrentRow.find_all('td', class_ = 'arrondi')[1]
                                  iconsCell = torrentRow.find_all('td', class_ = 'arrondi')[2]

                                  mainLink = popinCell.find('a', class_ = 'mtTool')
                                  name = mainLink.get_text().upper()

                                  subSoup = BeautifulSoup(mainLink['mtcontent'])
                                  ballon2 = subSoup.find('td', class_="ballon2")
                                  ballon4 = subSoup.find('td', class_="ballon4")

                                  splittedReleaseName = re.split('(\.[0-9]{4}\.)', name, flags=re.IGNORECASE)

                                  if len(splittedReleaseName) > 1:
                                      cleanedReleaseName = ''.join(splittedReleaseName[0:-2])

                                      match = re.compile(ur"[\w]+", re.UNICODE)
                                      nameSplit = ''.join(match.findall(unicodedata.normalize('NFKD', cleanedReleaseName).encode('ASCII','ignore')))
                                      titleSplit = ''.join(match.findall(unicodedata.normalize('NFKD', title.upper()).encode('ASCII','ignore')))

                                      if titleSplit == nameSplit and self.matchLanguage(media['info']['languages'], re.split('[\. ]', splittedReleaseName[-1])):
                                          downloadUrl = (l for l in iconsCell.find_all('a') if 'download' in l['href']).next()['href']
                                          parsed = urlparse.urlparse(downloadUrl)
                                          torrent_id = urlparse.parse_qs(parsed.query)['id']

                                          new = {}
                                          new['id'] = torrent_id
                                          new['name'] = name
                                          new['url'] = self.urls['home'] % (downloadUrl)
                                          new['detail_url'] = mainLink['href']

                                          try:
                                            new['size'] = self.parseSize(ballon2.contents[2])
                                          except:
                                             new['size'] = self.parseSize(ballon2.contents[2].contents[0])

                                          new['seeders'] = tryInt(ballon4.find_all('font')[1].get_text())
                                          new['leechers'] = tryInt(ballon4.find_all('font')[3].get_text())
                         
                                          results.append(new)
                              except:
                                  log.error('Failed getting results from %s: %s', (self.getName(), traceback.format_exc()))
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
            'Login': 'Se loguer',
            'returnto' : '/'
        }

    def loginSuccess(self, output):
        return 'pseudo ou mot de passe non valide' not in output.lower()

    loginCheckSuccess = loginSuccess


config = [{
    'name': 'fnt',
    'groups': [
        {
            'tab': 'searcher',
            'list': 'torrent_providers',
            'name': 'fnt',
            'description': 'See <a href="https://fnt.nu">FNT</a>',
            'wizard': True,
            'icon': 'iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAIAAACQkWg2AAAAUUlEQVR4nGNkwAY4OTmxijMwMDDhkqCaBkb80nC3ff/+HcJgebMXp2oRZ2o4iWQNLPgdQFUbkH2Px7YB9zQ8vgjY8GYvAycnJ9Y4ZYSL0ipYAbauEEExUDs9AAAAAElFTkSuQmCC',
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