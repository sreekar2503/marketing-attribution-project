"""
The schema contracts, tested against the real files they guard.

These exist because the schemas are only worth anything if they actually run.
An earlier version of this project shipped src/schemas.py that nothing imported,
while requirements.txt claimed pandera enforced it in CI on every push -- a
written claim with no mechanism behind it, which is precisely the failure mode
the project documents. Notebook 01 now validates at load; these tests pin that
the contracts still match the files, and that they reject what they should.

Skipped when data/raw/ is absent so the CI `validate` job stays runnable
without the raw datasets.
"""

from pathlib import Path

import pandas as pd
import pytest

pa = pytest.importorskip("pandera.pandas", reason="pandera not installed")

from src.schemas import (  # noqa: E402
    ADS_INDUSTRIES,
    CRM_SECTORS,
    validate_accounts,
    validate_ads,
    validate_pipeline,
)

RAW = Path("data/raw")
ADS = RAW / "ads_performance.csv"
ACCOUNTS = RAW / "crm_sales_opps/accounts.csv"
PIPELINE = RAW / "crm_sales_opps/sales_pipeline.csv"

needs_raw = pytest.mark.skipif(
    not ADS.exists(), reason="data/raw/ not present"
)


# --- the contracts hold against the real files --------------------------------

@needs_raw
def test_ads_schema_accepts_the_real_file():
    assert len(validate_ads(pd.read_csv(ADS))) == 1_800


@needs_raw
def test_accounts_schema_accepts_the_real_file():
    assert len(validate_accounts(pd.read_csv(ACCOUNTS))) == 85


@needs_raw
def test_pipeline_schema_accepts_the_real_file():
    """
    8,800 rows including the ~16% with a null account. Nullable there is a
    statement that missing is legitimate -- unlike `sector`, where it is a bug.
    """
    assert len(validate_pipeline(pd.read_csv(PIPELINE))) == 8_800


# --- and reject what they are there to catch ----------------------------------

def test_ads_schema_rejects_a_misspelled_industry():
    """`Helthcare` is the constraint that was missing at the source."""
    bad = pd.DataFrame({
        "industry": ["Helthcare"], "ad_spend": [100.0], "revenue": [500.0],
        "impressions": [1000], "clicks": [50], "conversions": [5],
    })
    with pytest.raises(pa.errors.SchemaErrors):
        validate_ads(bad)


def test_ads_schema_rejects_an_impossible_funnel():
    """Clicks above impressions. Nothing in the source enforces this."""
    bad = pd.DataFrame({
        "industry": ["SaaS"], "ad_spend": [100.0], "revenue": [500.0],
        "impressions": [10], "clicks": [500], "conversions": [5],
    })
    with pytest.raises(pa.errors.SchemaErrors):
        validate_ads(bad)


def test_accounts_schema_rejects_the_corrected_spelling():
    """
    The inversion that makes the point: `technolgy` passes because it is what
    the source actually contains; `technology` fails. Once a typo is
    load-bearing, silently accepting its fix is its own kind of drift.
    """
    assert "technolgy" in CRM_SECTORS
    assert "technology" not in CRM_SECTORS

    bad = pd.DataFrame({
        "account": ["Acme"], "sector": ["technology"], "revenue": [1000.0],
    })
    with pytest.raises(pa.errors.SchemaErrors):
        validate_accounts(bad)


def test_pipeline_schema_rejects_an_unknown_deal_stage():
    bad = pd.DataFrame({
        "opportunity_id": ["O1"], "account": ["Acme"],
        "deal_stage": ["Closed"], "close_value": [500.0],
    })
    with pytest.raises(pa.errors.SchemaErrors):
        validate_pipeline(bad)


# --- the vocabularies stay in step with the crosswalk -------------------------

def test_vocabularies_match_the_crosswalk():
    """
    If someone adds a category to a schema without adding a crosswalk row, the
    partition tests in test_crosswalk.py would still pass -- they check the
    crosswalk against the outputs, not against the schemas. This closes that gap.
    """
    x = pd.read_csv("output/industry_crosswalk.csv", keep_default_na=False)
    assert set(x.loc[x["ads_industry"] != "", "ads_industry"]) == set(ADS_INDUSTRIES)
    assert set(x.loc[x["crm_sector"] != "", "crm_sector"]) == set(CRM_SECTORS)
