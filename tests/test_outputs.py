"""
Invariants on the committed outputs.

These pin the figures the README quotes. If a notebook re-run changes a headline
number, this fails loudly rather than leaving the README silently wrong -- which
is the same class of bug the project documents.
"""

import numpy as np
import pandas as pd
import pytest

AD_SPEND_TOTAL = 11_108_749.09
CRM_REVENUE_TOTAL = 10_005_534.00
ADS_REPORTED_REVENUE = 54_183_330.81
DEALS_WON = 4_238
N_ACCOUNTS = 85
N_AD_ROWS = 1_800


@pytest.fixture(scope="module")
def ads():
    return pd.read_csv("output/ads_by_industry.csv")


@pytest.fixture(scope="module")
def crm():
    return pd.read_csv("output/crm_by_sector.csv")


@pytest.fixture(scope="module")
def before_after():
    return pd.read_csv("output/before_after_comparison.csv").set_index("stage")


# --- totals the README quotes -------------------------------------------------

def test_ad_spend_total(ads):
    assert np.isclose(ads["ad_spend"].sum(), AD_SPEND_TOTAL, atol=0.01)


def test_crm_revenue_total(crm):
    assert np.isclose(crm["crm_revenue"].sum(), CRM_REVENUE_TOTAL, atol=0.01)


def test_row_and_account_counts(ads, crm):
    assert ads["n_ad_rows"].sum() == N_AD_ROWS
    assert crm["n_accounts"].sum() == N_ACCOUNTS
    # 4,238 arrived at independently confirms no Won deal has a null account
    assert crm["deals_won"].sum() == DEALS_WON


# --- the headline claim -------------------------------------------------------

def test_naive_join_matches_nothing(before_after):
    """The finding. If this ever passes non-zero, the premise has changed."""
    naive = before_after.loc["naive_join"]
    assert naive["matched_categories"] == 0
    assert naive["ad_spend_coverage"] == 0.0
    assert naive["crm_revenue_coverage"] == 0.0


def test_reconciled_coverage(before_after):
    rec = before_after.loc["reconciled_crosswalk"]
    assert rec["matched_categories"] == 4
    assert np.isclose(rec["ad_spend_coverage"], 0.7932, atol=0.001)
    assert np.isclose(rec["crm_revenue_coverage"], 0.5253, atol=0.001)


# --- denominators are comparable across stages --------------------------------

def test_denominators_are_stable(before_after):
    """
    Coverage is only comparable before/after if the denominators do not move.
    This is why match_rate was removed: len(naive) changes when a crosswalk
    collapses categories, so it could not be compared across notebooks.
    """
    for col in ["ad_spend_total", "crm_revenue_total", "ads_categories", "crm_categories"]:
        assert before_after[col].nunique() == 1, f"{col} differs between stages"


def test_matched_never_exceeds_total(before_after):
    assert (before_after["ad_spend_matched"] <= before_after["ad_spend_total"]).all()
    assert (before_after["crm_revenue_matched"] <= before_after["crm_revenue_total"]).all()


def test_revenue_definition_gap(before_after):
    """The 5.4x gap between platform-reported and CRM closed-won revenue."""
    gap = before_after["revenue_definition_gap"].unique()
    assert len(gap) == 1
    assert np.isclose(gap[0], ADS_REPORTED_REVENUE / CRM_REVENUE_TOTAL, atol=0.001)


# --- the sensitivity band -----------------------------------------------------
#
# Added after the project priced one uncertain mapping and called the other
# "unmeasurable." Both are priced now, and the headline is a range rather than a
# point, so the range needs pinning the same way the point did.

@pytest.fixture(scope="module")
def sens():
    return pd.read_csv("output/sensitivity.csv").set_index("scenario")


def test_base_case_row_matches_the_headline(sens, before_after):
    """The sensitivity base case and the before/after 'after' row are the same run."""
    base = sens.loc["Base case (as shipped)"]
    rec = before_after.loc["reconciled_crosswalk"]
    assert np.isclose(base["ad_spend_coverage"], rec["ad_spend_coverage"])
    assert np.isclose(base["crm_revenue_coverage"], rec["crm_revenue_coverage"])
    assert base["ad_delta_pp"] == 0 and base["crm_delta_pp"] == 0


def test_the_coverage_band(sens):
    """62.0-79.3% of ad spend, 33.9-67.7% of CRM revenue."""
    assert np.isclose(sens["ad_spend_coverage"].min(), 0.6200, atol=0.001)
    assert np.isclose(sens["ad_spend_coverage"].max(), 0.7932, atol=0.001)
    assert np.isclose(sens["crm_revenue_coverage"].min(), 0.3387, atol=0.001)
    assert np.isclose(sens["crm_revenue_coverage"].max(), 0.6768, atol=0.001)


def test_the_medium_mapping_costs_more_than_the_low_one(sens):
    """
    The finding that justifies pricing every uncertain mapping rather than only
    the one that felt uncertain. If this ever flips, the README's argument that
    confidence ranks support and not stakes no longer holds and must be rewritten.
    """
    tech = abs(sens.loc["technolgy -> SaaS (fold the Low-confidence sector in)", "crm_delta_pp"])
    ecom = abs(sens.loc["E-commerce -> retail dropped (reject the Medium mapping)", "crm_delta_pp"])
    assert np.isclose(tech, 15.15, atol=0.05)
    assert np.isclose(ecom, 18.66, atol=0.05)
    assert ecom > tech, "the Medium mapping no longer costs more than the Low one"


def test_the_two_decisions_push_in_opposite_directions(sens):
    """Excluding technolgy understates; including E-commerce->retail overstates."""
    tech = sens.loc["technolgy -> SaaS (fold the Low-confidence sector in)", "crm_delta_pp"]
    ecom = sens.loc["E-commerce -> retail dropped (reject the Medium mapping)", "crm_delta_pp"]
    assert tech > 0 > ecom


def test_only_the_crm_side_moves_for_technolgy(sens):
    """technolgy is a CRM sector; folding it in cannot change ad spend coverage."""
    row = sens.loc["technolgy -> SaaS (fold the Low-confidence sector in)"]
    assert row["ad_delta_pp"] == 0
