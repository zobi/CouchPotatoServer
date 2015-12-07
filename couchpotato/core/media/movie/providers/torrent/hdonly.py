from couchpotato.core.logger import CPLog
from couchpotato.core.media._base.providers.torrent.hdonly import Base
from couchpotato.core.media.movie.providers.base import MovieProvider

log = CPLog(__name__)

autoload = 'hdonly'


class hdonly(MovieProvider, Base):
    pass