"""Demo data -- sincefirst runs with no API key.

Eight listings, and every one of them is a real measurement from 2026-08-20
rather than a number I liked the look of. Six of the eight are the actual
view/age pairs that came back from Etsy; the titles are changed, the arithmetic
is not.

The point of the set is the two pairs that sit almost on top of each other in
views and nowhere near each other in meaning -- because that pair is the whole
reason this program exists, and a demo that does not contain it is a demo of
nothing.
"""
DAY = 86400

# (title, views, age in days, favourites) -- ages measured, not invented.
ROWS = [
    # THE PAIR. 6 views apart, 164x apart in rate.
    ("Pottery template bundle, 12 shapes", 335, 16, 21),
    ("Friesian cow enamel pin", 341, 2554, 9),

    # THE OTHER PAIR, from the silver ring search: near-identical counts,
    # sixteen years and sixteen times apart.
    ("Masonic signet ring, 1970s", 24287, 4515, 431),
    ("Crystal ring mystery box", 23815, 279, 1288),

    # The busiest thing measured in six searches, and it is genuinely busy.
    ("Art deco diamond ring, 1920s", 1004450, 1171, 64328),

    # A third of every search looks like this. Four years up, nobody has opened
    # it. That is the loudest number on the page and Etsy never shows it.
    ("Hand-turned beech bowl, small", 0, 1400, 0),

    # Between a fifth and a half of a search is younger than the cutoff.
    ("Linocut, wren and raven", 3, 4, 1),

    # And the middle of the distribution: one look every three days.
    ("Speckled stoneware mug", 124, 372, 18),

    # A quarter of everything measured is below 0.065 a day. Without a row here
    # the "barely" band was written, shipped, and never once printed.
    ("Brass curtain tie-backs, pair", 12, 1100, 2),
]

# One listing where Etsy gave a view count but no first-listed date. Rare, but
# the "unknown" branch existed for months in an earlier app without ever being
# reached, so it gets a row of its own rather than a promise.
NO_DATE = ("Wooden shoe last, unmarked", 91, None, 4)


def demo_listings(now):
    out = []
    for i, (title, views, age, favs) in enumerate(ROWS + [NO_DATE]):
        lid = 940000001 + i
        out.append({
            "listing_id": lid,
            "title": title,
            # No URL. The ids are not real listings, and a link that 404s is
            # worse than no link -- giftlist shipped six broken thumbnails that
            # way before anyone noticed.
            "url": "",
            "views": views,
            "num_favorers": favs,
            "original_creation_timestamp": (now - age * DAY) if age is not None else None,
            # Renewed today, like every listing measured. Present so the demo
            # exercises the rule that this field is NOT the age.
            "creation_timestamp": now,
            "price": {"amount": 1800 + i * 700, "divisor": 100, "currency_code": "GBP"},
        })
    return out
