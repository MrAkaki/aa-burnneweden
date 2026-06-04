from esi.openapi_clients import ESIClientProvider

from . import __version__

esi = ESIClientProvider(
    compatibility_date="2025-12-16",
    ua_appname="aa-burnneweden",
    ua_version=__version__,
    ua_url="https://github.com/MrAkaki/aa-burnneweden",
    tags=["Contracts"],
)
