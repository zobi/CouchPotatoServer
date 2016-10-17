from couchpotato.core.logger import CPLog
from couchpotato.core.media._base.providers.torrent.bluetigers import Base
from couchpotato.core.media.movie.providers.base import MovieProvider

log = CPLog(__name__)

autoload = 'bluetigers'


class bluetigers(MovieProvider, Base):
    pass