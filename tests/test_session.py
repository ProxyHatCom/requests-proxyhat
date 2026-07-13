"""Tests for ProxyHatSession — verifies real requests routing through the mocked
transport, so sticky reuse and per-request rotation are exercised end to end offline."""

import re

import requests

from requests_proxyhat import ProxyHatSession

_SID = re.compile(r"-sid-([0-9a-f]+)-")


def sid_of(url):
    match = _SID.search(url)
    return match.group(1) if match else None


def make_session(**kw):
    session = ProxyHatSession(username="ph-1", password="pw", **kw)
    session.trust_env = False  # ignore any ambient HTTP(S)_PROXY env in CI
    return session


class TestSticky:
    def test_pins_proxies_on_session(self):
        session = make_session(country="us")
        assert session.proxies["http"] == session.proxies["https"]
        assert session.proxies["http"].startswith("http://ph-1-country-us")
        assert "-ttl-30m" in session.proxies["http"]

    def test_same_ip_reused_across_requests(self, capture_proxies):
        session = make_session(country="us")
        session.get("http://example.com/a")
        session.get("http://example.com/b")
        assert len(capture_proxies) == 2
        # Same pinned session id both times -> one residential IP for the session.
        assert sid_of(capture_proxies[0]) == sid_of(capture_proxies[1])
        assert sid_of(capture_proxies[0]) is not None

    def test_custom_ttl(self):
        session = make_session(sticky="2h")
        assert "-ttl-2h" in session.proxies["http"]


class TestRotating:
    def test_no_session_proxies_pinned(self):
        session = make_session(sticky=False)
        # Nothing pinned on the session; each request injects its own proxy.
        assert session.proxies == {}

    def test_fresh_ip_per_request(self, capture_proxies):
        session = make_session(country="us", sticky=False)
        session.get("http://example.com/a")
        session.get("http://example.com/b")
        assert len(capture_proxies) == 2
        # Each request mints a fresh gateway session -> different exit IP each time.
        assert sid_of(capture_proxies[0]) != sid_of(capture_proxies[1])
        assert all(p.startswith("http://ph-1-country-us") for p in capture_proxies)

    def test_explicit_proxies_override_wins(self, capture_proxies):
        session = make_session(sticky=False)
        session.get("http://example.com", proxies={"http": "http://override:9@host:1"})
        assert capture_proxies == ["http://override:9@host:1"]


class TestTargeting:
    def test_geo_and_socks5(self, capture_proxies):
        session = make_session(country="de", region="berlin", city="berlin", filter="high", protocol="socks5")
        session.get("http://example.com")
        proxy = capture_proxies[0]
        assert proxy.startswith("socks5://ph-1-country-de")
        assert "-region-berlin" in proxy
        assert "-city-berlin" in proxy
        assert "-filter-high" in proxy
        assert proxy.endswith("@gate.proxyhat.com:1080")

    def test_get_returns_mocked_response(self, capture_proxies):
        session = make_session(country="us")
        resp = session.get("http://example.com")
        assert isinstance(resp, requests.Response)
        assert resp.status_code == 200
