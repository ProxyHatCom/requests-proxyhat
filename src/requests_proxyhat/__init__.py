"""requests-proxyhat — route Python ``requests`` through ProxyHat residential proxies."""

from requests_proxyhat._resolve import ProxyHatConfigError, resolve_credentials
from requests_proxyhat.session import ProxyHatSession, proxyhat_proxies

__all__ = [
    "ProxyHatConfigError",
    "ProxyHatSession",
    "proxyhat_proxies",
    "resolve_credentials",
]
__version__ = "0.1.0"
