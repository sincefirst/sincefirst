"""Etsy Open API v3. Public listing data only -- no OAuth, no shop, no buyer data.

TRAP: `x-api-key` is the keystring AND the shared secret joined by a colon.
Sending the keystring alone is a 403 that looks like a wrong key.

Every field this program reads -- views, num_favorers, original_creation_timestamp,
title, url -- comes back on /listings/active with an application key.
"""
import json
import urllib.error
import urllib.parse
import urllib.request

BASE = "https://api.etsy.com/v3/application"
PAGE = 100


class EtsyError(Exception):
    pass


def client(api_key):
    if not api_key:
        return None

    def get(path, params=None):
        url = BASE + path
        if params:
            url += "?" + urllib.parse.urlencode({k: v for k, v in params.items()
                                                 if v not in (None, "")})
        req = urllib.request.Request(url, headers={
            "x-api-key": api_key,
            "Accept": "application/json",
        })
        try:
            with urllib.request.urlopen(req, timeout=30) as f:
                return json.load(f)
        except urllib.error.HTTPError as e:
            raise EtsyError("%s %s: %s" % (path.split("?")[0], e.code,
                                           e.read()[:160].decode("utf-8", "replace")))

    class Client:
        def search(self, keywords, limit=PAGE):
            data = get("/listings/active", {
                "keywords": keywords,
                "limit": min(limit, PAGE),
                "is_safe": "true",
            })
            return data.get("results") or []

        def fetch(self, ids):
            """listings/batch is all-or-nothing, so a group that fails is retried
            one at a time -- a watch list is a set of ids that stop existing."""
            out = []
            ids = [str(i) for i in ids]
            for i in range(0, len(ids), 20):
                group = ids[i:i + 20]
                try:
                    out += (get("/listings/batch",
                                {"listing_ids": ",".join(group)}).get("results") or [])
                except EtsyError:
                    for one in group:
                        try:
                            out += (get("/listings/batch",
                                        {"listing_ids": one}).get("results") or [])
                        except EtsyError:
                            pass  # gone
            return out

    return Client()
