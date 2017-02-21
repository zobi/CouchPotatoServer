from couchpotato.core.logger import CPLog
from couchpotato.core.media._base.providers.torrent.t411api import Base
from couchpotato.core.media.movie.providers.base import MovieProvider

log = CPLog(__name__)

autoload = 't411api'


class t411api(MovieProvider, Base):
    pass
