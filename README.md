# requests-proxyhat

Route Python [requests](https://github.com/psf/requests) through [ProxyHat](https://proxyhat.com?utm_source=github&utm_medium=readme&utm_campaign=requests) residential proxies — a drop-in `Session` that pins one residential IP for the whole session by default, plus rotation, geo-targeting and socks5.

[![CI](https://github.com/ProxyHatCom/requests-proxyhat/actions/workflows/ci.yml/badge.svg)](https://github.com/ProxyHatCom/requests-proxyhat/actions/workflows/ci.yml)
[![Compatible with requests latest](https://github.com/ProxyHatCom/requests-proxyhat/actions/workflows/compat.yml/badge.svg)](https://github.com/ProxyHatCom/requests-proxyhat/actions/workflows/compat.yml)
[![PyPI](https://img.shields.io/pypi/v/requests-proxyhat)](https://pypi.org/project/requests-proxyhat/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

> [!TIP]
> **Recommended proxies — [ProxyHat](https://proxyhat.com?utm_source=github&utm_medium=readme&utm_campaign=requests&utm_content=callout) residential IPs.** Every feature in this package is tested end-to-end against ProxyHat and works great. First-class integration; also works with any proxy, or none.


## Why

Scraping or calling APIs from a datacenter IP gets you rate-limited, CAPTCHA-walled and blocked. `requests` already speaks proxies through its `proxies={"http": ..., "https": ...}` dict — this package fills that dict with ProxyHat's residential IPs (50M+ across 148+ countries) and wires it into a `Session` subclass, so `session.get(url)` just works through a residential IP. No fork, no boilerplate.

## Install

```bash
pip install requests-proxyhat
```

## Quick start

```python
from requests_proxyhat import ProxyHatSession

# An API key auto-selects an active residential sub-user:
with ProxyHatSession(country="us") as session:   # sticky US IP for the whole session
    print(session.get("https://api.ipify.org").text)
    print(session.get("https://api.ipify.org").text)  # same IP — cookies stay coherent
```

Get an API key at [proxyhat.com](https://proxyhat.com?utm_source=github&utm_medium=readme&utm_campaign=requests).

Just want the proxies dict for plain `requests` or your own `Session`?

```python
import requests
from requests_proxyhat import proxyhat_proxies

proxies = proxyhat_proxies(country="de")   # {"http": "http://…@gate.proxyhat.com:8080", "https": …}
requests.get("https://api.ipify.org", proxies=proxies)
```

## Credentials

Pass them explicitly or via environment variables — options win over env:

| Option | Env var | Notes |
|---|---|---|
| `api_key` | `PROXYHAT_API_KEY` | Auto-selects an active sub-user with remaining traffic |
| `sub_user` | `PROXYHAT_SUBUSER` | Pick a specific sub-user by uuid or name (with an API key) |
| `username` | `PROXYHAT_USERNAME` | Explicit gateway `proxy_username` (skips the API) |
| `password` | `PROXYHAT_PASSWORD` | Explicit gateway `proxy_password` |

## Targeting

```python
ProxyHatSession(
    protocol="http",   # or "socks5"
    country="us",      # ISO code or "any" (default)
    region="california",
    city="new_york",
    filter="high",     # AI IP-quality tier
    sticky="30m",      # session lifetime (default); sticky=False rotates every request
)
```

### Sticky session vs rotation

A `Session` usually means "keep talking to this site as one visitor" — logging in, paging, keeping cookies. If the exit IP changed mid-session the site would see a user teleporting between cities and block it. So `ProxyHatSession` is **sticky by default**: one residential IP is pinned for the session (`sticky="30m"`, set on `session.proxies`), keeping cookies and fingerprint coherent.

Want a fresh IP on **every** request instead (e.g. many independent one-shot fetches)? Turn stickiness off:

```python
with ProxyHatSession(country="us", sticky=False) as session:   # rotating residential IP per request
    for url in urls:
        session.get(url)   # each request exits from a new IP
```

Set a custom lifetime with `sticky="2h"`.

The standalone `proxyhat_proxies(...)` dict is stateless, so it **rotates by default** (`sticky=None`); pass `sticky="30m"` to pin one IP in that dict too.

## How it works

`ProxyHatSession` resolves your gateway credentials (via the official [`proxyhat`](https://pypi.org/project/proxyhat/) SDK — an API key auto-picks an active sub-user, or pass `username`/`password`), then builds a proxy URL where the username carries ProxyHat's targeting grammar (`<user>-country-us-sid-<id>-ttl-30m`) and points at the gateway (`http://gate.proxyhat.com:8080`, or `socks5://…:1080`). Sticky mode sets that URL on `session.proxies` once, so every request reuses one pinned residential IP. Rotating mode overrides `Session.request()` to mint a fresh gateway session per call — so each request exits from a new IP, and `requests`' connection pool can't pin you to one, since the proxy URL itself changes.

## License

MIT © [ProxyHat](https://proxyhat.com)
