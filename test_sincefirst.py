#!/usr/bin/env python3
"""Zero-dependency test runner. `python test_sincefirst.py`.

Dividing one number by another is easy to get right. The tests that matter are
about the three ways the inputs lie: a view count with no time base, a creation
date that is really a renewal date, and a zero that means two different things.
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from lib.etsy import client
from lib.mock import demo_listings
from lib.rate import (BARELY, BAR_WIDTH, FORBIDDEN_WORDS, MEASURED_N,
                      MEDIAN_RATE, NO_TIME_BASE, QUIET, RENEWAL_IS_NOT_AGE,
                      STEADY, TOO_YOUNG_DAYS, TOO_YOUNG_NOTE, VERDICT_TEXT,
                      age_days, bar, describe, first_listed, human_age,
                      rate_of, verdict, views_of)
import sincefirst as S

DAY = 86400
NOW = 1787200000
_pass = _fail = 0


def t(name):
    def deco(fn):
        global _pass, _fail
        try:
            fn()
            _pass += 1
        except Exception as e:                       # noqa: BLE001
            _fail += 1
            print("  FAIL  %s\n        %s" % (name, e))
    return deco


def eq(a, b, m=""):
    if a != b:
        raise AssertionError("%s expected %r, got %r" % (m, b, a))


def ok(v, m="expected truthy"):
    if not v:
        raise AssertionError(m)


def L(views=100, age=100, **kw):
    d = {"listing_id": 1, "title": "x", "url": "", "views": views,
         "creation_timestamp": NOW, "num_favorers": 0}
    d["original_creation_timestamp"] = None if age is None else NOW - int(age * DAY)
    d.update(kw)
    return d


# ------------------- RULE 1: a count with no time base says nothing
@t("the measured pair: 6 views apart, 164 times apart in rate")
def _():
    a = rate_of(L(views=335, age=16), NOW)
    b = rate_of(L(views=341, age=2554), NOW)
    eq(round(a, 2), 20.94)
    eq(round(b, 3), 0.134)
    ok(a / b > 150, "the pair no longer differs by two orders of magnitude: %.1f" % (a / b))


@t("the second measured pair, from the ring search")
def _():
    old = rate_of(L(views=24287, age=4515), NOW)
    new = rate_of(L(views=23815, age=279), NOW)
    ok(new > old * 15, "%.2f vs %.2f" % (new, old))
    eq(verdict(L(views=24287, age=4515), NOW), "steady")
    eq(verdict(L(views=23815, age=279), NOW), "busy")


@t("the note carries the measurement, not just the claim")
def _():
    ok("335" in NO_TIME_BASE and "341" in NO_TIME_BASE)
    ok("2,554" in NO_TIME_BASE)


@t("a view count is never printed without an age beside it")
def _():
    # Chi cac DONG DU LIEU, thut vao dung 6 cot. Ban dau assertion nay quet moi
    # dong va vo trung chinh doan van dang giai thich cap 335/341 -- cung mot
    # kieu loi da mac o palette, howlong va exportr.
    out = S.render(demo_listings(NOW), NOW, demo=True)
    rows = [l for l in out.split("\n")
            if re.match(r"^ {6}\S", l) and re.search(r"\d[\d,]* views", l)]
    ok(len(rows) >= 8, "found only %d data rows to check" % len(rows))
    for line in rows:
        ok("over" in line or "no first-listed date" in line,
           "a bare view count: %r" % line.strip())


# ------------- RULE 2: the age is original_creation, never creation
@t("creation_timestamp is ignored entirely")
def _():
    # Renewed today, first listed two years ago. Using the renewal date would
    # divide by zero days and report an enormous rate.
    l = L(views=730, age=730, creation_timestamp=NOW)
    eq(round(rate_of(l, NOW), 2), 1.0)


@t("a listing with no original_creation date gets no rate")
def _():
    eq(rate_of(L(views=500, age=None), NOW), None)
    eq(verdict(L(views=500, age=None), NOW), "unknown")


@t("a date in the future is refused rather than made negative")
def _():
    l = L(views=10, age=0)
    l["original_creation_timestamp"] = NOW + 10 * DAY
    eq(age_days(l, NOW), None)
    eq(rate_of(l, NOW), None)


@t("the renewal note says what it is about")
def _():
    ok("renewal" in RENEWAL_IS_NOT_AGE.lower())
    ok("first listed" in RENEWAL_IS_NOT_AGE.lower())


# ----------------------- RULE 3: zero is two different things
@t("zero views on an old listing is 'unseen'")
def _():
    eq(verdict(L(views=0, age=1400), NOW), "unseen")


@t("zero views on a new listing is 'young', not 'unseen'")
def _():
    eq(verdict(L(views=0, age=3), NOW), "young")
    eq(rate_of(L(views=0, age=3), NOW), None)


@t("the cutoff is stated, with how much of a search it covers")
def _():
    ok(str(TOO_YOUNG_DAYS) in TOO_YOUNG_NOTE)
    ok("20 to 50" in TOO_YOUNG_NOTE, "the measured share is missing")


@t("one day either side of the cutoff behaves differently")
def _():
    eq(rate_of(L(views=50, age=TOO_YOUNG_DAYS - 1), NOW), None)
    ok(rate_of(L(views=50, age=TOO_YOUNG_DAYS + 1), NOW) is not None)


@t("a missing or nonsense view count is not a zero")
def _():
    eq(views_of({"views": None}), None)
    eq(views_of({}), None)
    eq(views_of({"views": -4}), None)
    eq(views_of({"views": True}), None, "a bool slipped through as a count:")
    eq(views_of({"views": 0}), 0, "a real zero must survive:")


# ------------------------ the bands come from the measurement
@t("the bands sit where the measured quartiles are")
def _():
    eq((BARELY, QUIET, STEADY), (0.1, 1.0, 10.0))
    ok(0.06 < MEDIAN_RATE < 5, "the median moved: %s" % MEDIAN_RATE)
    eq(MEASURED_N, 395)


@t("each band is entered at its own boundary")
def _():
    eq(verdict(L(views=9, age=1000), NOW), "barely")     # 0.009
    eq(verdict(L(views=500, age=1000), NOW), "quiet")    # 0.5
    eq(verdict(L(views=5000, age=1000), NOW), "steady")  # 5
    eq(verdict(L(views=50000, age=1000), NOW), "busy")   # 50


@t("every band has wording")
def _():
    for k in ("young", "unseen", "barely", "quiet", "steady", "busy", "unknown"):
        ok(VERDICT_TEXT.get(k), "no text for %s" % k)


# ---------------------------- RULE 4: a linear bar would lie
@t("the bar is logarithmic, so a 100x gap is not a 100x gap in width")
def _():
    small, big = len(bar(1.0)), len(bar(100.0))
    ok(big < small * 3, "the bar looks linear: %d vs %d" % (small, big))
    ok(big > small, "the bar does not grow at all")


@t("the busiest rate measured fills the bar without overflowing it")
def _():
    # 857.4 la muc cao nhat do duoc, va tren thang log toi 1000 no gan nhu day.
    # Do la dac tinh cua thang do chu khong phai loi: cai phai bao dam la khong
    # co gi TRAN ra ngoai.
    eq(len(bar(857.4)), BAR_WIDTH)
    eq(len(bar(999999.0)), BAR_WIDTH, "a huge rate must clamp, not overflow")
    ok(len(bar(100.0)) < BAR_WIDTH, "100/day already fills the bar, so the top is too low")


@t("nothing and zero draw no bar at all")
def _():
    eq(bar(None), "")
    eq(bar(0), "")


@t("the axis is drawn, and under the bars rather than at the margin")
def _():
    out = S.render(demo_listings(NOW), NOW, demo=True).split("\n")
    axis = [l for l in out if "0.01" in l and "1000" in l]
    ok(axis, "no axis line")
    ok("log scale" in "\n".join(out), "the log scale is never mentioned")
    eq(len(axis[0]) - len(axis[0].lstrip()), 15, "the axis is not under the bars:")


# ---------------------------- RULE 5: no verdict on the verdict
@t("no output line judges the listing")
def _():
    out = S.render(demo_listings(NOW), NOW, demo=True).lower()
    for w in FORBIDDEN_WORDS:
        ok(w not in out, 'the output contains "%s"' % w)


@t("the page says outright that a rate is not a recommendation")
def _():
    out = S.render(demo_listings(NOW), NOW, demo=True)
    ok("not a recommendation" in out)


# --------------------------------------------------- the demo
@t("the demo is deterministic")
def _():
    eq(demo_listings(NOW), demo_listings(NOW))


@t("no demo listing is dated in the future")
def _():
    for l in demo_listings(NOW):
        ts = l["original_creation_timestamp"]
        ok(ts is None or ts <= NOW, "%s is dated ahead" % l["title"])


@t("the demo reaches every band, so no branch ships unprinted")
def _():
    seen = {verdict(l, NOW) for l in demo_listings(NOW)}
    for k in ("young", "unseen", "barely", "quiet", "steady", "busy", "unknown"):
        ok(k in seen, "the demo never produces %s" % k)


@t("the demo carries the pair the program exists for")
def _():
    rates = sorted(r for r in (rate_of(l, NOW) for l in demo_listings(NOW)) if r)
    ok(max(rates) / min(rates) > 1000, "the demo has no real spread")


@t("no demo listing carries a made-up URL")
def _():
    for l in demo_listings(NOW):
        eq(l["url"], "", "%s has a fabricated link" % l["title"])


@t("the heading counts the rows rather than asserting a number")
def _():
    out = S.render(demo_listings(NOW), NOW, demo=True,
                   heading="%d listings" % len(demo_listings(NOW)))
    eq("%d listings" % len(demo_listings(NOW)) in out, True)


# -------------------------------------------------- odds and ends
@t("an empty result set says so instead of drawing an empty chart")
def _():
    out = S.render([], NOW)
    ok("Nothing came back" in out)
    ok("log scale" not in out, "it drew an axis for no data")


@t("ages read as English")
def _():
    eq(human_age(0.5), "today")
    eq(human_age(16), "16 days")
    eq(human_age(372), "1.0 years")   # moc doi tu 730 xuong 365 ngay
    eq(human_age(300), "10 months")
    eq(human_age(2554), "7.0 years")
    eq(human_age(None), "unknown")


@t("a singular favourite is not plural")
def _():
    out = S.render([L(views=100, age=100, num_favorers=1, title="one")], NOW)
    ok("1 favourite" in out and "1 favourites" not in out)


@t("titles arrive HTML-escaped and are decoded")
def _():
    # Measured 2026-08-20 over 300 live titles: &#39; 21 times, &quot; 19.
    eq(describe(L(title="Men&#39;s mug"), NOW)["title"], "Men's mug")
    eq(describe(L(title="A &quot;wonky&quot; bowl"), NOW)["title"], 'A "wonky" bowl')
    eq(describe(L(title="R&amp;D"), NOW)["title"], "R&D")
    eq(describe(L(title="plain title"), NOW)["title"], "plain title")


@t("no entity code ever reaches the screen")
def _():
    rows = [L(title="Men&#39;s leather &quot;wallet&quot;", views=500, age=500)]
    out = S.render(rows, NOW)
    ok("&#39;" not in out and "&quot;" not in out, "an entity code was printed")
    want = chr(77) + chr(101) + chr(110) + chr(39) + chr(115) + ' leather ' + chr(34) + 'wallet' + chr(34)
    ok(want in out, 'decoded title not found')


@t("a long title is wrapped, not cut off mid-word")
def _():
    # Real titles reach 150 characters (measured over 300). The first draft cut
    # at 66 with no marker, so a title just stopped and read like corruption.
    long_title = ("Tasse personalisiert mit Namen Beste Freundin Geburtstag Geschenk "
                  "Frau Geschenkidee beste Freundin Geschenk Weihnachten beste Freundin")
    out = S.render([L(title=long_title, views=500, age=500)], NOW)
    ok(long_title.split()[-1] in out, "the end of the title was thrown away")
    for line in out.split(chr(10)):
        ok(len(line) < 90, "a line ran to %d characters: %r" % (len(line), line[:60]))


@t("no key means no client, and the demo runs instead")
def _():
    eq(client(""), None)
    eq(client(None), None)
    ok(client("abc:def") is not None)


@t("describe returns every field the report prints")
def _():
    d = describe(L(), NOW)
    for k in ("listing_id", "title", "url", "views", "age_days", "first_listed",
              "rate", "verdict", "favourites"):
        ok(k in d, "describe is missing %s" % k)


print("\n%d/%d passed" % (_pass, _pass + _fail))
sys.exit(1 if _fail else 0)
