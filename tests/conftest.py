"""Shared test doubles.

``capture_proxies`` monkeypatches the transport adapter so no bytes hit the
network: it records the proxy URL ``requests`` resolves for each call (after the
Session merges ``self.proxies`` / per-request ``proxies=``), then returns a canned
200 response. That lets the session tests assert exactly which residential proxy
each ``session.get(...)`` would dial — sticky reuse vs rotation — fully offline.
"""

from __future__ import annotations

import pytest
import requests
from requests.adapters import HTTPAdapter
from requests.utils import select_proxy


@pytest.fixture
def capture_proxies(monkeypatch):
    used: list[str | None] = []

    def fake_send(self, request, **kwargs):
        proxies = kwargs.get("proxies") or {}
        used.append(select_proxy(request.url, proxies))
        response = requests.Response()
        response.status_code = 200
        response._content = b"ok"
        response.url = request.url
        response.request = request
        return response

    monkeypatch.setattr(HTTPAdapter, "send", fake_send)
    return used
