"""
The crosswalk is the project's central claim: a complete, non-overlapping
partition of both vocabularies, with every mapping justified in writing.

These tests exist because a hand-typed mapping can contain the exact class of
error it was written to fix. They are lifted out of 03_reconciliation.ipynb so
they run on every push rather than only when someone opens the notebook.
"""

import pandas as pd
import pytest

CROSSWALK = "output/industry_crosswalk.csv"
ADS = "output/ads_by_industry.csv"
CRM = "output/crm_by_sector.csv"

VALID_CONFIDENCE = {"High", "Medium", "Low", "Gap"}


@pytest.fixture(scope="module")
def xwalk():
    # keep_default_na=False is the whole point of test_gap_survives_roundtrip
    # below; read it the way the notebook does, not the way pandas defaults.
    return pd.read_csv(CROSSWALK, keep_default_na=False)


@pytest.fixture(scope="module")
def ads():
    return pd.read_csv(ADS)


@pytest.fixture(scope="module")
def crm():
    return pd.read_csv(CRM)


def test_partitions_ads_vocabulary(xwalk, ads):
    """Every ads industry appears exactly once. No category silently dropped."""
    mapped = xwalk.loc[xwalk["ads_industry"] != "", "ads_industry"]
    assert mapped.is_unique, "an ads industry is mapped more than once"
    assert set(mapped) == set(ads["industry"]), (
        "crosswalk and ads data disagree on the ads vocabulary"
    )


def test_partitions_crm_vocabulary(xwalk, crm):
    """Every CRM sector appears exactly once, including the unmapped ones."""
    mapped = xwalk.loc[xwalk["crm_sector"] != "", "crm_sector"]
    assert mapped.is_unique, "a CRM sector is mapped more than once"
    assert set(mapped) == set(crm["sector"]), (
        "crosswalk and CRM data disagree on the CRM vocabulary"
    )


def test_confidence_is_a_closed_set(xwalk):
    """No free-text confidence values. This is the field most likely to drift."""
    unexpected = set(xwalk["confidence"]) - VALID_CONFIDENCE
    assert not unexpected, f"unexpected confidence values: {unexpected}"


def test_gap_survives_csv_roundtrip():
    """
    Regression test for a real bug in this project: 'None' as a confidence value
    round-tripped out of CSV as NaN, collapsing 'documented gap' into 'missing
    value' -- precisely the failure mode the project is about.
    """
    default_read = pd.read_csv(CROSSWALK)
    assert not default_read["confidence"].isna().any(), (
        "a confidence value parses as NaN on a default read; "
        "documented gaps are being collapsed into missing values"
    )


def test_every_mapping_has_a_rationale(xwalk):
    """A mapping without a written reason is not reviewable."""
    blank = xwalk[xwalk["rationale"].str.strip() == ""]
    assert blank.empty, f"{len(blank)} row(s) have no rationale"


def test_gap_rows_map_to_nothing(xwalk):
    """A row marked Gap must not also assert a mapping."""
    gaps = xwalk[xwalk["confidence"] == "Gap"]
    both_sides = gaps[(gaps["ads_industry"] != "") & (gaps["crm_sector"] != "")]
    assert both_sides.empty, "a row is marked Gap but maps both vocabularies"
