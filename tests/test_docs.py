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

So: retired figures may not reappear, and every headline figure the documents
quote must equal what the pipeline actually produced.
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


# --- quoted headline figures match the pipeline -------------------------------

def _nums(s):
    """Every number in the text, commas stripped, as a set of strings."""
    return {m.replace(",", "") for m in re.findall(r"\d[\d,]*(?:\.\d+)?", s)}


@pytest.mark.parametrize("doc", sorted(DOCS))
def test_totals_quoted_are_the_real_totals(doc, text, before_after):
    """
    Both documents lead on the two headline totals. If a notebook re-run moved
    either, the prose must move with it -- this is the check that was missing.
    """
    n = _nums(text[doc])
    ad_total = before_after["ad_spend_total"].iloc[0]
    crm_total = before_after["crm_revenue_total"].iloc[0]

    # Full precision or the abbreviated $11.1M / $10.0M form; either counts.
    assert (f"{ad_total:.0f}" in n) or (f"{ad_total/1e6:.1f}" in n), \
        f"{doc} does not quote the real ad spend total ({ad_total:,.0f})"
    assert (f"{crm_total:.0f}" in n) or (f"{crm_total/1e6:.1f}" in n), \
        f"{doc} does not quote the real CRM revenue total ({crm_total:,.0f})"


@pytest.mark.parametrize("doc", sorted(DOCS))
def test_coverage_percentages_quoted_are_real(doc, text, before_after):
    """
    The 0% → 79.3% / 52.5% result, at whatever precision the document chooses.
    The README quotes one decimal; EXECUTIVE_SUMMARY.md rounds to 79% and 53%
    because it is written for a non-technical reader, and that is correct rather
    than sloppy. What must not vary is the underlying number, so both the exact
    and rounded renderings are accepted -- and nothing else is.
    """
    rec = before_after.loc["reconciled_crosswalk"]
    n = _nums(text[doc])
    for label, value in [
        ("ad spend coverage", rec["ad_spend_coverage"]),
        ("crm revenue coverage", rec["crm_revenue_coverage"]),
    ]:
        pct = value * 100
        accepted = {f"{pct:.1f}", f"{round(pct):d}"}
        assert accepted & n, (
            f"{doc} does not quote the real {label} ({value:.1%}); "
            f"expected one of {sorted(accepted)}"
        )


def test_event_counts_agree_across_both_documents(text):
    """
    326,812 conversions vs 4,238 won deals is the one cross-system contrast that
    survived the trim, and it now carries the argument in both files. If it is
    corrected in one place it has to be corrected in both.
    """
    for count in ["326812", "4238"]:
        present = [d for d in DOCS if count in _nums(text[d])]
        assert len(present) == len(DOCS), (
            f"{count} appears only in {present} -- the two documents disagree"
        )


def test_won_deals_figure_matches_the_data(text):
    """And that contrast is not just internally consistent, but correct."""
    crm = pd.read_csv("output/crm_by_sector.csv")
    won = int(crm["deals_won"].sum())
    for doc in DOCS:
        assert str(won) in _nums(text[doc]), f"{doc} disagrees with deals_won={won}"
