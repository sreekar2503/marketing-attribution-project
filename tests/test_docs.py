"""
The prose is bound to the data.

Written after the project committed its own central failure twice over. The
revenue-ratio figures were removed from README.md as uninterpretable, but the
same numbers survived in EXECUTIVE_SUMMARY.md and in a second spot further down
the README itself. Two documents, one retired figure, and nothing checking that
they agreed -- doc drift, in a project about doc drift, with no mechanism
binding it. The manual grep that found the second instance only ran because a
reviewer asked; that is precisely the "only protects you if someone remembers
to run it" problem the CI layer exists to solve.

So: retired figures may not reappear, and every figure the documents quote must
be a rendering of a number the pipeline actually produced.

What these checks do and do not guarantee
-----------------------------------------
The value checks are SUBSET assertions -- every figure of a given shape must be
justified -- not presence assertions. That distinction is load-bearing: an
earlier version asked only whether the correct value appeared somewhere in the
file, which passes while the prose states something false, as long as the right
number survives in a table further down.

What they still do not catch is a figure that is individually legitimate but in
the wrong place: swapping `79.3%` for `52.5%` passes, because both are real
outputs. Binding each figure to its own label would catch that, and is done
below for the two event counts, where the anchor words are stable. It is not
done for the coverage and dollar figures, which appear in prose, tables, chart
captions and callouts with no consistent surrounding phrasing -- an anchor there
would be brittle enough to fail on rewording, which trains people to ignore it.
The limitation is real and is recorded here rather than papered over.
"""

import re
from pathlib import Path

import pandas as pd
import pytest

DOCS = {
    "README.md": Path("README.md"),
    "EXECUTIVE_SUMMARY.md": Path("EXECUTIVE_SUMMARY.md"),
}

# Deliberately retired. Ratios between the two revenue figures are not
# like-for-like: non-overlapping periods, different event definitions. They were
# removed because a number that precise invites being read at face value.
RETIRED = {
    "5.4x": "platform-vs-CRM revenue ratio",
    "8.1x": "revenue-per-dollar divergence",
    "4.84": "platform-reported revenue per ad dollar",
    "0.60x": "CRM-anchored revenue per ad dollar",
    "54,183": "platform-reported revenue, full precision",
    "54.2M": "platform-reported revenue, abbreviated",
}


@pytest.fixture(scope="module")
def before_after():
    return pd.read_csv("output/before_after_comparison.csv").set_index("stage")


@pytest.fixture(scope="module")
def text():
    return {name: path.read_text() for name, path in DOCS.items()}


# --- retired figures stay retired ---------------------------------------------

@pytest.mark.parametrize("doc", sorted(DOCS))
def test_no_retired_figures(doc, text):
    """
    Catches the exact regression that happened: a figure stripped from one
    document surviving in another, or lower down in the same one.
    """
    found = [f"{fig} ({why})" for fig, why in RETIRED.items() if fig in text[doc]]
    assert not found, f"{doc} quotes retired figure(s): {'; '.join(found)}"


# --- every figure quoted must be one the pipeline produced ---------------------
#
# These are SUBSET assertions, not presence assertions, and the distinction is
# the whole point. An earlier version asked "does the correct number appear
# somewhere in this file?" -- which passes while the document states something
# false, as long as the right value survives anywhere else in the same file.
# Replacing every `79.3%` in the prose with `81.4%` went green, because `79.3pp`
# in a table downstream satisfied the check. A check that reports success while
# the artefact is wrong is the exact failure this project documents.
#
# So the direction is inverted: extract EVERY figure of the given shape, and
# require the whole set to be renderings of numbers the pipeline actually
# produced. A wrong value anywhere fails, and cannot be masked by a right one.

# `\b` must apply to `pp` only. Anchoring it after the alternation instead --
# `(?:%|pp)\b` -- silently matches nothing ending in `%`, because `%` and the
# space after it are both non-word characters, so there is no boundary between
# them. That version extracted the `pp` figures, ignored every percentage, and
# reported green. It is in this file's history; the mutation tests caught it.
PCT = re.compile(r"(\d+(?:\.\d+)?)\s*(?:%|pp\b)")
USD = re.compile(r"\\?\$\s*(\d[\d,]*(?:\.\d+)?)\s*([MK]?)")

# Structural or upstream figures with no cell in output/ to bind them to.
#   0, 100 -- rhetorical denominators ("100% unreconciled", "do not chase 100%")
#   16     -- share of CRM deals with a null account, computed in notebook 01
#             from the raw pipeline and never persisted to output/. Listed here
#             rather than derived so this test stays runnable without data/raw/.
CONTEXTUAL_PCT = {"0", "0.0", "100", "16"}
CONTEXTUAL_USD = {"0", "0.00"}


def _pct(value):
    """Percentage renderings this project uses: one decimal, or rounded."""
    return {f"{value:.1f}", f"{round(value)}"}


@pytest.fixture(scope="module")
def accepted_pct():
    """Every percentage the pipeline can justify, at either precision."""
    ba = pd.read_csv("output/before_after_comparison.csv")
    mix = pd.read_csv("output/mix_comparison.csv")
    crm = pd.read_csv("output/crm_by_sector.csv")
    sens = pd.read_csv("output/sensitivity.csv")

    ok = set(CONTEXTUAL_PCT)
    # The sensitivity band: every scenario's coverage, and every delta. The
    # README and the executive summary both quote from this, at both precisions.
    for col in ["ad_spend_coverage", "crm_revenue_coverage"]:
        for v in sens[col]:
            ok |= _pct(v * 100)
    for col in ["ad_delta_pp", "crm_delta_pp"]:
        for v in sens[col]:
            ok |= _pct(abs(v))
    for col in ["ad_spend_coverage", "crm_revenue_coverage", "category_match_rate"]:
        for v in ba[col]:
            ok |= _pct(v * 100)
    for col in ["spend_share", "revenue_share"]:
        for v in mix[col]:
            ok |= _pct(v * 100)
    for v in mix["gap_pp"]:
        ok |= _pct(abs(v))

    # The technolgy sensitivity: its share of CRM revenue, and the coverage that
    # folding it into SaaS would produce. Both are quoted; neither is a column.
    total = crm["crm_revenue"].sum()
    tech = crm.loc[crm["sector"] == "technolgy", "crm_revenue"].sum()
    matched = ba["crm_revenue_matched"].max()
    ok |= _pct(tech / total * 100)
    ok |= _pct((matched + tech) / total * 100)
    return ok


@pytest.fixture(scope="module")
def accepted_usd():
    """Every dollar figure the pipeline can justify: plain forms and $X.XM."""
    ba = pd.read_csv("output/before_after_comparison.csv")
    crm = pd.read_csv("output/crm_by_sector.csv")
    ads = pd.read_csv("output/ads_by_industry.csv")

    values = set()
    for col in ["ad_spend_total", "ad_spend_matched",
                "crm_revenue_total", "crm_revenue_matched"]:
        values |= set(ba[col])
    values |= set(crm["crm_revenue"]) | set(ads["ad_spend"])
    sens = pd.read_csv("output/sensitivity.csv")
    values |= set(sens["ad_spend_matched"]) | set(sens["crm_revenue_matched"])

    # Derived, and quoted: the unreconciled remainders in the before/after chart,
    # and the technolgy-inclusive alternative in the sensitivity table.
    ad_t, crm_t = ba["ad_spend_total"].iloc[0], ba["crm_revenue_total"].iloc[0]
    ad_m, crm_m = ba["ad_spend_matched"].max(), ba["crm_revenue_matched"].max()
    tech = crm.loc[crm["sector"] == "technolgy", "crm_revenue"].sum()
    values |= {ad_t - ad_m, crm_t - crm_m, crm_m + tech}

    plain, millions = set(CONTEXTUAL_USD), set()
    for v in values:
        plain |= {f"{v:.2f}", f"{v:.0f}"}
        millions |= {f"{v / 1e6:.1f}", f"{v / 1e6:.2f}"}
    return plain, millions


@pytest.mark.parametrize("doc", sorted(DOCS))
def test_every_percentage_is_a_real_figure(doc, text, accepted_pct):
    """A wrong percentage anywhere fails, even if the right one appears too."""
    found = {m.group(1) for m in PCT.finditer(text[doc])}
    unjustified = sorted(found - accepted_pct, key=float)
    assert not unjustified, (
        f"{doc} quotes percentage(s) the pipeline does not produce: "
        f"{unjustified}"
    )


@pytest.mark.parametrize("doc", sorted(DOCS))
def test_every_dollar_figure_is_a_real_figure(doc, text, accepted_usd):
    """Same inversion for money, including the abbreviated $X.XM form."""
    plain, millions = accepted_usd
    unjustified = []
    for m in USD.finditer(text[doc]):
        raw, suffix = m.group(1).replace(",", ""), m.group(2)
        if suffix == "M":
            if raw not in millions:
                unjustified.append(f"${raw}M")
        elif raw not in plain:
            unjustified.append(f"${raw}")
    assert not unjustified, (
        f"{doc} quotes dollar figure(s) the pipeline does not produce: "
        f"{sorted(set(unjustified))}"
    )


# --- the cross-system event contrast ------------------------------------------

CONVERSIONS = re.compile(r"([\d,]+)\s*\*{0,2}\s*\n?\s*conversions")
WON_DEALS = re.compile(r"([\d,]+)\s*\*{0,2}\s*\n?\s*won deals")


@pytest.mark.parametrize("doc", sorted(DOCS))
def test_event_counts_are_correct_wherever_they_are_stated(doc, text):
    """
    326,812 conversions against 4,238 won deals is the contrast that survived
    the trim, and it now carries the argument in both files.

    Anchored on the words rather than searched for as bare digits: this reads
    the number actually attached to "conversions" and to "won deals" and checks
    THAT value, so a wrong figure fails even if the right one appears elsewhere
    in the file. `deals_won` is bound to the data; the platform conversion count
    is a raw-side figure with no cell in output/, so it is pinned as a constant.
    """
    won = int(pd.read_csv("output/crm_by_sector.csv")["deals_won"].sum())
    for pattern, label, expected in [
        (WON_DEALS, "won deals", won),
        (CONVERSIONS, "conversions", 326_812),
    ]:
        stated = [int(m.group(1).replace(",", "")) for m in pattern.finditer(text[doc])]
        assert stated, f"{doc} no longer states a {label} count"
        wrong = [v for v in stated if v != expected]
        assert not wrong, f"{doc} states {label} as {wrong}, expected {expected:,}"


def test_both_documents_state_the_contrast(text):
    """Neither file may quietly drop the argument the other one makes."""
    for doc in DOCS:
        assert CONVERSIONS.search(text[doc]), f"{doc} dropped the conversions count"
        assert WON_DEALS.search(text[doc]), f"{doc} dropped the won-deals count"
