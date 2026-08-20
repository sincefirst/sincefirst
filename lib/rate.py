"""The rules. Pure, and the only part of sincefirst worth testing hard.

Etsy publishes `views` on every search result. It is the one number on a listing
that looks like evidence of interest, and on its own it is unreadable.
"""
from datetime import datetime, timezone

DAY = 86400

# RULE 1 -- A VIEW COUNT WITH NO TIME BASE IS NOT A NUMBER YOU CAN READ.
#
# Measured on one search of a hundred "ceramic mug" listings, the two closest in
# view count that were furthest apart in age:
#
#     335 views in     16 days  =  21.51 a day
#     341 views in  2,554 days  =   0.13 a day
#
# Six views apart, and a hundred and sixty-four times apart in what they mean.
# The same search again on "silver ring": 24,287 views over 4,515 days (5.4 a
# day) sitting beside 23,815 views over 279 days (85.4 a day).
#
# Etsy prints the left-hand number and never the right-hand one. So this program
# never shows a view count without the age beside it, and sorts on the rate.
NO_TIME_BASE = (
    "Etsy publishes a lifetime view count and no age to read it against. "
    "Measured on one search of 100 listings, 335 views and 341 views sat side by "
    "side -- one of them collected over 16 days, the other over 2,554. This page "
    "divides by the age instead, and shows both numbers."
)


# RULE 2 -- THE AGE IS `original_creation_timestamp`. NEVER `creation_timestamp`.
#
# `creation_timestamp` moves every time Etsy renews a listing, and Etsy renews
# constantly: all five of the most-viewed listings in each measured search had a
# creation date of TODAY. Dividing by that age gives a rate of infinity for
# everything, every morning.
#
# The same field pair caught newdrop out, from the other direction.
RENEWAL_IS_NOT_AGE = (
    "Age is counted from when the seller first listed the item, not from Etsy's "
    "renewal date. Every one of the most-viewed listings in the measured searches "
    "had been renewed today, so the renewal date would make everything look new."
)


# TITLES ARRIVE HTML-ESCAPED. Measured 2026-08-20 over 300 live titles:
# `&#39;` 21 times, `&quot;` 19 times. Printed raw they read as rubbish in the
# middle of a word -- Men&#39;s -- and there is no reason to make a reader parse
# entity codes. Decoded once, on the way in.
#
# `html.unescape` is in the standard library and handles the numeric forms too,
# so nothing is hand-rolled here.
def decode(text):
    import html
    return html.unescape(text) if isinstance(text, str) else text


def first_listed(listing):
    """Seconds since the seller first put the item up, or None."""
    ts = (listing or {}).get("original_creation_timestamp")
    return ts if isinstance(ts, int) and ts > 0 else None


def age_days(listing, now):
    ts = first_listed(listing)
    if ts is None or ts > now:
        return None
    return (now - ts) / DAY


def views_of(listing):
    v = (listing or {}).get("views")
    # A bool is an int in Python and would sail through as 0 or 1.
    if isinstance(v, bool) or not isinstance(v, int) or v < 0:
        return None
    return v


# RULE 3 -- ZERO VIEWS IS NOT "NEW", AND IT IS NOT ALWAYS INFORMATION.
#
# A third of every search measured came back with no views at all: 34, 38 and 39
# out of 100. Zero on something listed this morning says nothing -- nobody has
# had the chance. Zero on something listed four years ago is the loudest number
# on the page. The two are the same integer and must not print the same.
#
# Below this many days a rate is not reported at all, because one view on day one
# is 1.0 a day and that is an artefact, not a measurement.
TOO_YOUNG_DAYS = 14


def rate_of(listing, now):
    """Views a day since first listed, or None when it cannot honestly be given."""
    v = views_of(listing)
    age = age_days(listing, now)
    if v is None or age is None or age < TOO_YOUNG_DAYS:
        return None
    return v / max(age, 1.0)


# The bands, taken from the measured distribution rather than from a feeling
# about what "a lot" means. 395 listings across six searches, 2026-08-20:
#
#     p25   0.065 a day        under  0.1 a day  ->  32% of listings
#     p50   0.333 a day        under  1   a day  ->  61%
#     p75   4.669 a day        under 10   a day  ->  83%
#     p90  30.692 a day        max              857.4 a day
#
# So the middle listing on Etsy is looked at ABOUT ONCE EVERY THREE DAYS, and
# the bands below are round numbers sitting near the measured quartiles. They
# split 32 / 29 / 22 / 17, which is close enough to even that no band is a
# curiosity.
BARELY = 0.1
QUIET = 1.0
STEADY = 10.0

MEDIAN_RATE = 0.333
MEASURED_N = 395


def verdict(listing, now):
    """One of: young, unseen, barely, quiet, steady, busy, unknown."""
    v = views_of(listing)
    age = age_days(listing, now)
    if v is None or age is None:
        return "unknown"
    if age < TOO_YOUNG_DAYS:
        return "young"
    if v == 0:
        return "unseen"
    r = v / max(age, 1.0)
    if r < BARELY:
        return "barely"
    if r < QUIET:
        return "quiet"
    if r < STEADY:
        return "steady"
    return "busy"


# RULE 4 -- A LINEAR BAR LIES ABOUT THIS DATA.
#
# The rates measured span 0.00 to 857.4 views a day -- more than five orders of
# magnitude. Drawn linearly, everything except the single busiest listing is a
# bar of zero width, which reads as "none of these get looked at". The bars are
# logarithmic, and the page says so, because a log axis nobody mentions is its
# own kind of lie.
BAR_WIDTH = 34
LOG_TOP = 1000.0  # a full bar; above the busiest rate measured (857.4)


def bar(rate, width=BAR_WIDTH):
    """A log-scale bar. 0.01/day is one cell, 1000/day fills it."""
    if rate is None:
        return ""
    if rate <= 0:
        return ""
    import math
    lo = math.log10(0.01)
    hi = math.log10(LOG_TOP)
    frac = (math.log10(max(rate, 0.01)) - lo) / (hi - lo)
    n = max(1, min(width, round(frac * width)))
    return "█" * n


# RULE 5 -- A RATE IS NOT A RECOMMENDATION.
#
# Busy does not mean good and unseen does not mean bad; plenty of the quietest
# things measured were one-off vintage pieces, which is the whole reason someone
# is on Etsy. This program reports the number and the age and stops. There is a
# test that fails the build if any of these words reaches the screen.
FORBIDDEN_WORDS = ["bargain", "popular choice", "hot", "trending", "must-buy",
                   "underrated", "hidden gem", "overpriced", "avoid", "best seller"]

VERDICT_TEXT = {
    "young": "listed too recently for a rate to mean anything yet",
    "unseen": "no views at all, over the whole time it has been listed",
    "barely": "under one look every ten days",
    "quiet": "under one look a day",
    "steady": "a few looks a day",
    "busy": "ten or more looks a day",
    "unknown": "Etsy gave no view count or no first-listed date",
}

# A fifth to a half of every search is younger than TOO_YOUNG_DAYS -- measured
# 26, 50, 30, 34, 20 and 45 out of 100 across the six searches. That is far too
# many to leave off the page without saying so, and far too many to invent a
# rate for.
TOO_YOUNG_NOTE = (
    "Anything listed in the last %d days is shown without a rate. Between a fifth "
    "and a half of a search is usually that new (measured: 20 to 50 out of 100), "
    "and one view on day two is not half a view a day, it is noise."
) % TOO_YOUNG_DAYS


def stamp(ts):
    if not isinstance(ts, int) or ts <= 0:
        return "unknown"
    return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d")


def human_age(days):
    if days is None:
        return "unknown"
    if days < 1:
        return "today"
    if days < 60:
        return "%d days" % round(days)
    if days < 365:
        return "%d months" % round(days / 30.44)
    return "%.1f years" % (days / 365.25)


def describe(listing, now):
    """Everything the report needs about one listing, measured once."""
    return {
        "listing_id": (listing or {}).get("listing_id"),
        "title": decode((listing or {}).get("title") or "") or "(untitled)",
        "url": (listing or {}).get("url") or "",
        "views": views_of(listing),
        "age_days": age_days(listing, now),
        "first_listed": stamp(first_listed(listing)),
        "rate": rate_of(listing, now),
        "verdict": verdict(listing, now),
        "favourites": (listing or {}).get("num_favorers"),
    }
