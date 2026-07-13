"""A ``requests.Session`` that routes every request through ProxyHat residential proxies.

``requests`` sends traffic through a proxy via the ``proxies={"http": ..., "https": ...}``
mapping — either per request or, once, on a ``Session``. ``ProxyHatSession`` is a
``Session`` subclass that resolves your ProxyHat gateway credentials, builds that
mapping with the SDK's targeting grammar, and wires it in so ``session.get(url)``
just works through a residential IP.

Sticky by default: one residential IP is pinned for the whole session (set on
``self.proxies``), so cookies and fingerprint stay consistent across requests.
Pass ``sticky=False`` to rotate — a fresh gateway session (and residential IP) is
minted per request by overriding :meth:`request`.

``proxyhat_proxies(...)`` returns the plain ``{"http": url, "https": url}`` dict for
callers who want to drop it into ``requests.get(..., proxies=...)`` or their own
``Session`` without subclassing.
"""

from __future__ import annotations

from typing import Any

import requests
from proxyhat import build_connection_url

from requests_proxyhat._resolve import resolve_credentials

# Sensible default for a Session: pin one residential IP for its lifetime so
# cookies, logins and fingerprint stay consistent across requests.
DEFAULT_STICKY = "30m"


def proxyhat_proxies(
    *,
    api_key: str | None = None,
    username: str | None = None,
    password: str | None = None,
    sub_user: str | None = None,
    country: str | None = None,
    region: str | None = None,
    city: str | None = None,
    sticky: bool | str | None = None,
    filter: str | None = None,
    protocol: str = "http",
) -> dict[str, str]:
    """Return a plain ``requests`` proxies dict for the ProxyHat gateway.

    The result is ``{"http": url, "https": url}`` where ``url`` is a full
    ``http://<user>-country-us:<pass>@gate.proxyhat.com:8080`` (or ``socks5://…:1080``)
    connection URL. Hand it to ``requests.get(url, proxies=...)`` or
    ``session.proxies.update(...)``.

    Rotating by default (``sticky=None``): a stateless dict, so the gateway hands
    out a fresh residential IP per connection. Pass ``sticky="30m"`` (or ``True``)
    to pin one IP — but note a reused dict then keeps that same pinned IP; for a
    managed sticky session use :class:`ProxyHatSession` instead.

    Geo/quality targeting: ``country`` (ISO code or ``"any"``), ``region``,
    ``city``, ``filter`` (AI IP-quality tier). ``protocol`` is ``"http"`` or ``"socks5"``.
    """
    user, pw = resolve_credentials(
        api_key=api_key,
        username=username,
        password=password,
        sub_user=sub_user,
    )
    url = build_connection_url(
        username=user,
        password=pw,
        country=country,
        region=region,
        city=city,
        sticky=sticky,
        filter=filter,
        protocol=protocol,
    )
    return {"http": url, "https": url}


class ProxyHatSession(requests.Session):
    """``requests.Session`` pre-wired to the ProxyHat residential gateway.

    ```python
    from requests_proxyhat import ProxyHatSession

    with ProxyHatSession(country="us") as s:   # sticky US IP for the whole session
        print(s.get("https://api.ipify.org").text)
    ```

    Sticky vs rotating:

    - ``sticky="30m"`` (default) or ``sticky=True`` pins one residential IP for the
      session — set on ``self.proxies`` and reused by every request.
    - ``sticky=False`` (or ``None``) rotates: :meth:`request` mints a fresh gateway
      session per call, so each request exits from a new residential IP.

    Credentials resolve exactly like the other ProxyHat integrations (options win
    over env): ``api_key`` / ``PROXYHAT_API_KEY`` auto-picks an active sub-user, or
    pass ``username`` + ``password``. Geo/quality: ``country``, ``region``, ``city``,
    ``filter``. ``protocol`` is ``"http"`` or ``"socks5"``.
    """

    def __init__(
        self,
        *,
        api_key: str | None = None,
        username: str | None = None,
        password: str | None = None,
        sub_user: str | None = None,
        country: str | None = None,
        region: str | None = None,
        city: str | None = None,
        sticky: bool | str | None = DEFAULT_STICKY,
        filter: str | None = None,
        protocol: str = "http",
    ) -> None:
        super().__init__()
        self._username, self._password = resolve_credentials(
            api_key=api_key,
            username=username,
            password=password,
            sub_user=sub_user,
        )
        self._country = country
        self._region = region
        self._city = city
        self._filter = filter
        self._protocol = protocol
        self._sticky = sticky

        if sticky:
            # Pin one IP for the whole session: build once (a single fixed session
            # id) and let every request reuse it via self.proxies.
            self.proxies = self._build_proxies(sticky=sticky)
        # Rotating: leave self.proxies empty; request() injects a fresh proxy per call.

    def _build_proxies(self, *, sticky: bool | str | None) -> dict[str, str]:
        url = build_connection_url(
            username=self._username,
            password=self._password,
            country=self._country,
            region=self._region,
            city=self._city,
            sticky=sticky,
            filter=self._filter,
            protocol=self._protocol,
        )
        return {"http": url, "https": url}

    def request(self, method: str, url: str, **kwargs: Any) -> requests.Response:
        """Send a request, injecting a fresh rotating proxy when not sticky.

        In rotating mode every call gets a brand-new gateway session id, so each
        request exits from a different residential IP — and ``requests``' connection
        pool can't pin you to one, since the proxy URL itself changes. A caller can
        still override with an explicit ``proxies=`` argument.
        """
        if not self._sticky and "proxies" not in kwargs:
            kwargs["proxies"] = self._build_proxies(sticky=True)
        return super().request(method, url, **kwargs)
