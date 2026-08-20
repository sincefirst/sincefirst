#!/usr/bin/env python3
"""sincefirst -- how much has anyone actually looked at this Etsy listing?

    python sincefirst.py find "linocut print"      search, ranked by rate
    python sincefirst.py look 1234567 7654321      specific listing ids

Set ETSY_API_KEY to "keystring:shared_secret" for live data. Without it the
program prints a fixed demo built from real measurements.
"""
import os
import sys
import textwrap
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from lib.etsy import EtsyError, client
from lib.mock import demo_listings
from lib.rate import (BARELY, BAR_WIDTH, FORBIDDEN_WORDS, LOG_TOP, MEASURED_N,
                      MEDIAN_RATE, NO_TIME_BASE, QUIET, RENEWAL_IS_NOT_AGE,
                      STEADY, TOO_YOUNG_DAYS, TOO_YOUNG_NOTE, VERDICT_TEXT,
                      bar, decode, describe, human_age)

ORDER = ["busy", "steady", "quiet", "barely", "unseen", "young", "unknown"]


def wrap(text, width=74, indent="  "):
    return textwrap.fill(text, width=width, initial_indent=indent,
                         subsequent_indent=indent).split("\n")


def scale_line():
    """The log axis, drawn. A log scale nobody labels is its own kind of lie."""
    import math
    lo, hi = math.log10(0.01), math.log10(LOG_TOP)
    marks = [(0.01, "0.01"), (0.1, "0.1"), (1, "1"), (10, "10"), (100, "100"), (1000, "1000")]
    row = [" "] * (BAR_WIDTH + 6)
    for value, label in marks:
        pos = int(round((math.log10(value) - lo) / (hi - lo) * BAR_WIDTH))
        for j, ch in enumerate(label):
            if 0 <= pos + j < len(row):
                row[pos + j] = ch
    return "".join(row).rstrip()


def render(rows, now, demo=False, heading=""):
    out = [""]
    out.append("  sincefirst%s" % ("   (demo data, real measurements)" if demo else ""))
    if heading:
        out.append("  %s" % heading)
    out.append("")
    out += wrap(NO_TIME_BASE)
    out.append("")

    described = sorted(
        (describe(r, now) for r in rows),
        key=lambda d: (ORDER.index(d["verdict"]),
                       -(d["rate"] if d["rate"] is not None else -1),
                       d["title"]),
    )

    if not described:
        out.append("  Nothing came back.")
        out.append("")
        return "\n".join(out)

    out.append("  views a day since first listed, on a log scale:")
    # Thanh bar bat dau o cot 15 ("    " + 9 ky tu so + "  "), nen truc phai
    # thut vao dung 15 cot. Lan dau toi de no o le trai va cac nhan so nam
    # lech han khoi thanh ma no dang danh dau -- mot truc dat sai cho con te
    # hon khong co truc.
    out.append(" " * 15 + scale_line())
    out.append("")

    last = None
    for d in described:
        if d["verdict"] != last:
            last = d["verdict"]
            out.append("  %s -- %s" % (last.upper(), VERDICT_TEXT[last]))
        rate = "%9.2f" % d["rate"] if d["rate"] is not None else "        -"
        out.append("    %s  %s" % (rate, bar(d["rate"])))
        # WRAPPED, NOT TRUNCATED. Real titles run to 150 characters (measured
        # over 300 live ones) and the first draft cut them at 66 with no
        # marker, so a title simply stopped mid-word and read like corruption.
        out += wrap(d["title"], width=76, indent="      ")
        views = "{:,}".format(d["views"]) if d["views"] is not None else "no"
        if d["age_days"] is None:
            # "91 views over unknown, first listed unknown" was the first draft
            # and reads like a bug rather than a fact about the data.
            detail = "      %s views, and Etsy gave no first-listed date to read them against" % views
        else:
            detail = "      %s views over %s, first listed %s" % (
                views, human_age(d["age_days"]), d["first_listed"])
        if isinstance(d["favourites"], int):
            detail += "   %s favourite%s" % ("{:,}".format(d["favourites"]),
                                             "" if d["favourites"] == 1 else "s")
        out.append(detail)
        if d["url"]:
            out.append("      %s" % d["url"])
        out.append("")

    out += wrap(RENEWAL_IS_NOT_AGE)
    out.append("")
    out += wrap(TOO_YOUNG_NOTE)
    out.append("")
    out += wrap(
        "For scale: across %d listings measured on 2026-08-20, the middle one was "
        "looked at %.2f times a day -- about once every three days. A quarter were "
        "under 0.065 a day. The busiest was 857." % (MEASURED_N, MEDIAN_RATE))
    out.append("")
    out += wrap(
        "A rate is not a recommendation. Plenty of the quietest things here are "
        "one-off vintage pieces, which is why people come to Etsy at all. This "
        "prints the number and the age and stops.")
    return "\n".join(out)


def main(argv):
    now = int(time.time())
    key = os.environ.get("ETSY_API_KEY", "").strip()
    api = client(key)

    cmd = argv[0] if argv else None
    rest = argv[1:]

    if cmd == "find":
        words = " ".join(rest).strip()
        if not words:
            print('usage: python sincefirst.py find "linocut print"', file=sys.stderr)
            return 2
        if not api:
            print("  find needs ETSY_API_KEY. Without one, run with no arguments "
                  "for the demo.", file=sys.stderr)
            return 2
        rows = api.search(words)
        print(render(rows, now, heading='the first %d results for "%s"' % (len(rows), words)))

    elif cmd == "look":
        ids = [a for a in rest if a.isdigit()]
        if not ids:
            print("usage: python sincefirst.py look <listing_id> ...", file=sys.stderr)
            return 2
        if not api:
            print("  look needs ETSY_API_KEY.", file=sys.stderr)
            return 2
        rows = api.fetch(ids)
        missing = len(ids) - len(rows)
        heading = "%d of %d listings" % (len(rows), len(ids))
        if missing:
            heading += "   (%d did not come back -- sold, ended or removed all "
            heading = heading % missing + "look the same from here)"
        print(render(rows, now, heading=heading))

    elif cmd in (None, "demo"):
        rows = demo_listings(now)
        # Counted, not typed. It said "eight listings" for a while after two
        # more were added to exercise the bands nobody had ever seen printed.
        print(render(rows, now, demo=True,
                     heading="%d listings, every number measured on 2026-08-20" % len(rows)))

    else:
        print("usage: python sincefirst.py [find|look|demo]", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv[1:]))
    except EtsyError as err:
        print("  Etsy said no: %s" % err, file=sys.stderr)
        sys.exit(1)
