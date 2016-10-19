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
        'login' : 'https://www.bluetigers.ca/account-login.php',
        'detail' : 'https://www.bluetigers.ca/torrents-details.php?id=%s',
        'download' : 'https://www.bluetigers.ca/download.php?id=%s',
        'search' : 'https://www.bluetigers.ca/torrents-search.php?',
        'home' : 'https://www.bluetigers.ca/%s',
    }

    http_time_between_calls = 1 #seconds

    def _search(self, media, quality, results):

        #urllib.urlencode( {'name': getTitle(media['info']) })
        for title in media['info']['titles']:
            try:
                TitleStringReal = str(title.encode("latin-1").replace('-',' '))
            
                url = self.urls['search'] + 'c59=1&c9=1&c56=1&c43=1&c20=1&c222=1&c22=1&c24=1&c26=1&' + urllib.urlencode( {'search': unicodedata.normalize('NFKD', title).encode('ASCII', 'ignore').replace('\'', ' ') }) + '&incldead=0&freeleech=0&lang=0'

                data = self.getHTMLData(url)
        
                if data:
                  html = BeautifulSoup(data)
                  try:
                      #Get first entry in table
                      torrentTable = html.find('table', class_ = 'ttable_headinner')

                      if torrentTable:
                          torrents = torrentTable.find_all('tr', class_=None)

                          for torrentRow in torrents[1:]:
                  
                              nameCell = torrentRow.find_all('td')[1]
                              downloadCell = torrentRow.find_all('td')[12]
                              sizeCell = torrentRow.find_all('td')[7]
                              seedersCell = torrentRow.find_all('td')[9]
                              leechersCell = torrentRow.find_all('td')[10]

                              name = nameCell.find_all('b')[0].get_text().upper()

                              splittedReleaseName = re.split('(\.[0-9]{4}\.)', name, flags=re.IGNORECASE)

                              if len(splittedReleaseName) > 1:
                                  cleanedReleaseName = ''.join(splittedReleaseName[0:-2])

                                  match = re.compile(ur"[\w]+", re.UNICODE)
                                  nameSplit = ''.join(match.findall(unicodedata.normalize('NFKD', cleanedReleaseName).encode('ASCII','ignore')))
                                  titleSplit = ''.join(match.findall(unicodedata.normalize('NFKD', title.upper()).encode('ASCII','ignore')))

                                  if titleSplit == nameSplit:
                                      downloadUrl = downloadCell.find('a')['href']
                                      parsed = urlparse.urlparse(downloadUrl)
                                      torrent_id = urlparse.parse_qs(parsed.query)['torrent']

                                      new = {}
                                      new['id'] = torrent_id
                                      new['name'] = name
                                      new['url'] =  self.urls['download'] % (torrent_id[0])
                                      new['detail_url'] = self.urls['detail'] % (torrent_id[0])
                                      new['size'] = self.parseSize(sizeCell.get_text())
                                      new['seeders'] = tryInt(seedersCell.get_text())
                                      new['leechers'] = tryInt(leechersCell.get_text())
                         
                                      results.append(new)
                  except:
                      log.error('Failed getting results from %s: %s', (self.getName(), traceback.format_exc()))
            except:
                continue
 
    def getLoginParams(self):
        return {
            'username': self.conf('username'),
            'password': self.conf('password'),
            'take_login': '1',
        }

    def loginSuccess(self, output):
        return output.lower() == ''

    loginCheckSuccess = loginSuccess


config = [{
    'name': 'bluetigers',
    'groups': [
        {
            'tab': 'searcher',
            'list': 'torrent_providers',
            'name': 'bluetigers',
            'description': 'See <a href="https://www.bluetigers.ca">Bluetigers</a>',
            'wizard': True,
            'icon': 'AAABAAEAEBAAAAEAIABoBAAAFgAAACgAAAAQAAAAIAAAAAEAIAAAAAAAAAQAAAAAAAAAAAAAAAAAAAAAAAA7LAv+EQwD/ks3Df6UbR3+tow4/q6GMv6ddST+fFsX/iYbB/4CAQH+KB0I/jQmCf4AAAH+Ew4E/kUzDP5JNQz+HBQF/icdB/6GYhf+qH4n/rSMO/6AXhj+b1ET/isgB/4EAgD+AAAA/ldBE/55Whv+BQMB/hcRBP5VPg7+VT4P/gcFAv5UPQ/+l24a/qF3If6AXhf+TjoN/hcRBP4IBAD+HRUE/jQqFv6Mcz/+qIdD/hkSBP4sIAn+clMV/lY/D/4pHgj+dVYU/odjGP5/XRb+Pi0L/hEMA/4/Lgz+kXU+/rmgcP7QvJT+6NWs/rOXXv4TDQL+QDAP/px2Kv47Kwr+Pi0L/mpOEv54VxX+RjMM/g8KAv59YCr+1rqC/qGSeP5rYFH+al1O/mdVO/5LPB3+EA4F/ldEGf67lEb+RzUT/iwgCP5eRRD+YEYR/hgSBf5gSh7+xa14/kJEQf4CR2v+AHmy/gB5uv4ARID+BAkT/hgVB/5+ZCj+yqhh/oxwNf4OCgP+SjYN/kIwC/4tIQn+u51e/jcwKP4FXoz+Edf0/gSmz/4EmdH+Baj1/gNPnP4lHgr+qoxK/uXNnf6Sdj3+AwIB/hgRBf4WEAP+cVcj/nNhMf4ABCD+AW7E/gJurv4KDBr+Di0+/gJMoP4AJXT+Tz8d/uTOo/7t27b+a1Ys/gQDAP4EAwD+FA4D/l9IFf4qIgn+AAUe/gUqi/4MQKf+AQQf/gwUK/4ACij+EAwS/sSrev7z6tX+59i4/j0vFP4FAwH+AQEB/hkSBf5UQBH+FhIE/gABCf4JDiz+L0J0/iA1eP4AAQj+FBEH/pWCWv7t3Lr+8uzb/s66lP4gFwv+BAMB/gAAAP4WEAT+NSgK/gkHA/4CAwH+CQgB/gkGBf4aFhL+XFE0/sKvhf705Mb+6Nq+/u3fwf6ah2P+CwkF/gEAAP4GBQL+IBcG/jkpCv5RPQ7+bVUW/qCCPP67oGP+waVo/tvAiv7q2bj+5NO0/u7hyP7s3cD+ybWN/jcsFv4hFwb+UTsO/n1ZFf6UbB/+o3or/q6CLv6wiUL+uJRU/q2MTv7dxJT+486j/qCHV/7Qt4r+6di4/uPPp/6yklT+a0wS/pBnGP6leCL+uIkx/q6ENf5dRhr+PCwQ/igeDf52XS/+0biH/t7Djv52Xi/+TzsW/uPFjP7gyqD+0bR8/odfF/6QZxj+mG0a/o9oHv44KA7+BwUB/gAAAP4FBAH+eGAx/tW3e/7ZuXz+e2Ew/jIhBv6Zfk7+5c+k/trCkv6HYBf/glwW/3tYFf8tIAj/AAAA/wEBAP8CAQH/OSwR/7eTSv/NrGz/1K1j/2pTKf8wIQT/YEca/9O9lP/q3cP/AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA==',
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
                }
            ],
        },
    ],
}]