"""Tests for proxyhat_proxies() and credential resolution — all offline."""

from types import SimpleNamespace

import pytest

from requests_proxyhat import ProxyHatConfigError, proxyhat_proxies, resolve_credentials


def sub_user(**kw):
    base = dict(
        uuid="u",
        name=None,
        proxy_username="ph-1",
        proxy_password="pw",
        traffic_limit=0,
        used_traffic=0,
        suspended_at=None,
    )
    base.update(kw)
    return SimpleNamespace(**base)


class TestProxiesDict:
    def test_http_https_url_shape(self):
        proxies = proxyhat_proxies(username="ph-1", password="pw", country="us")
        assert set(proxies) == {"http", "https"}
        assert proxies["http"] == proxies["https"]
        url = proxies["http"]
        assert url.startswith("http://ph-1-country-us")
        assert url.endswith("@gate.proxyhat.com:8080")
        assert ":pw@" in url

    def test_rotating_by_default(self):
        # A plain dict is stateless -> rotating: no pinned session id.
        url = proxyhat_proxies(username="ph-1", password="pw")["http"]
        assert "-sid-" not in url
        assert "-ttl-" not in url

    def test_sticky_pins_session(self):
        url = proxyhat_proxies(username="ph-1", password="pw", sticky="1h")["http"]
        assert "-sid-" in url
        assert "-ttl-1h" in url

    def test_geo_targeting(self):
        url = proxyhat_proxies(
            username="ph-1",
            password="pw",
            country="de",
            region="berlin",
            city="berlin",
            filter="high",
        )["http"]
        assert "ph-1-country-de" in url
        assert "-region-berlin" in url
        assert "-city-berlin" in url
        assert "-filter-high" in url

    def test_socks5_protocol(self):
        url = proxyhat_proxies(username="ph-1", password="pw", protocol="socks5")["http"]
        assert url.startswith("socks5://")
        assert url.endswith("@gate.proxyhat.com:1080")


class TestCredentialResolution:
    def test_explicit_username_password(self):
        assert resolve_credentials(username="ph-1", password="pw") == ("ph-1", "pw")

    def test_raises_without_credentials(self, monkeypatch):
        for var in ("PROXYHAT_API_KEY", "PROXYHAT_USERNAME", "PROXYHAT_PASSWORD", "PROXYHAT_SUBUSER"):
            monkeypatch.delenv(var, raising=False)
        with pytest.raises(ProxyHatConfigError):
            resolve_credentials()

    def test_env_username_password(self, monkeypatch):
        monkeypatch.setenv("PROXYHAT_USERNAME", "envuser")
        monkeypatch.setenv("PROXYHAT_PASSWORD", "envpass")
        assert resolve_credentials() == ("envuser", "envpass")

    def test_api_key_picks_active_sub_user(self, monkeypatch):
        users = [
            sub_user(uuid="s", proxy_username="susp", suspended_at="2026-01-01"),
            sub_user(uuid="g", proxy_username="exhausted", traffic_limit=100, used_traffic=100),
            sub_user(uuid="ok", proxy_username="ok", traffic_limit=100, used_traffic=1),
        ]
        fake_client = SimpleNamespace(sub_users=SimpleNamespace(list=lambda: users))
        monkeypatch.setattr("requests_proxyhat._resolve.ProxyHat", lambda **kw: fake_client)
        assert resolve_credentials(api_key="ph_key") == ("ok", "pw")

    def test_api_key_named_sub_user(self, monkeypatch):
        users = [sub_user(uuid="a", proxy_username="a"), sub_user(uuid="b", name="prod", proxy_username="b")]
        fake_client = SimpleNamespace(sub_users=SimpleNamespace(list=lambda: users))
        monkeypatch.setattr("requests_proxyhat._resolve.ProxyHat", lambda **kw: fake_client)
        assert resolve_credentials(api_key="ph_key", sub_user="prod") == ("b", "pw")

    def test_api_key_no_usable_sub_user(self, monkeypatch):
        users = [sub_user(traffic_limit=100, used_traffic=100)]
        fake_client = SimpleNamespace(sub_users=SimpleNamespace(list=lambda: users))
        monkeypatch.setattr("requests_proxyhat._resolve.ProxyHat", lambda **kw: fake_client)
        with pytest.raises(ProxyHatConfigError):
            resolve_credentials(api_key="ph_key")

    def test_proxies_resolve_via_api_key(self, monkeypatch):
        users = [sub_user(proxy_username="good", proxy_password="secret")]
        fake_client = SimpleNamespace(sub_users=SimpleNamespace(list=lambda: users))
        monkeypatch.setattr("requests_proxyhat._resolve.ProxyHat", lambda **kw: fake_client)
        url = proxyhat_proxies(api_key="ph_key", country="us")["http"]
        assert url.startswith("http://good-country-us")
        assert ":secret@gate.proxyhat.com:8080" in url
