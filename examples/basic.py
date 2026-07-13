"""Route Python requests through ProxyHat residential proxies.

Set PROXYHAT_API_KEY (auto-picks an active sub-user), or PROXYHAT_USERNAME +
PROXYHAT_PASSWORD, then run: python examples/basic.py
"""

from requests_proxyhat import ProxyHatSession, proxyhat_proxies

# 1. A managed sticky session — one residential IP pinned for its whole lifetime.
with ProxyHatSession(country="us") as session:
    print("sticky:", session.get("https://api.ipify.org").text)
    print("still same IP:", session.get("https://api.ipify.org").text)

# 2. Rotating — a fresh residential IP per request.
with ProxyHatSession(country="de", sticky=False) as session:
    print("rotating 1:", session.get("https://api.ipify.org").text)
    print("rotating 2:", session.get("https://api.ipify.org").text)

# 3. Just want the proxies dict for plain requests / your own Session?
import requests  # noqa: E402

proxies = proxyhat_proxies(country="gb")
print("plain dict:", requests.get("https://api.ipify.org", proxies=proxies).text)
