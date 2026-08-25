"""
Schema contracts, enforced at load.

The project's finding is that both systems accept anything and complain about
nothing: `technolgy` was written to the CRM because no constraint existed to
reject it. These schemas are that missing constraint, applied at the analysis
boundary instead. Import and call `validate_*` at the top of notebook 01.

    from src.schemas import validate_ads, validate_accounts, validate_pipeline
    ads = validate_ads(pd.read_csv("../data/raw/ads_performance.csv"))

Vocabularies are declared as closed sets deliberately. A new value should stop
the pipeline and force someone to add a crosswalk row -- not flow silently into
an unmatched bucket. That is the entire argument of the project, as code.
"""

import pandera.pandas as pa
from pandera.pandas import Check, Column, DataFrameSchema

# Frozen vocabularies. Changing these requires updating industry_crosswalk.csv,
# which tests/test_crosswalk.py then re-validates as a complete partition.
ADS_INDUSTRIES = ["E-commerce", "EdTech", "Fintech", "Healthcare", "SaaS"]

# `technolgy` is misspelled in the source and is listed that way on purpose.
# The schema documents reality, not the intent -- and freezing the existing typo
# is exactly what makes a *new* typo detectable. Do not "fix" this line.
CRM_SECTORS = [
    "employment", "entertainment", "finance", "marketing", "medical",
    "retail", "services", "software", "technolgy", "telecommunications",
]

ads_schema = DataFrameSchema(
    {
        "industry": Column(str, Check.isin(ADS_INDUSTRIES), nullable=False),
        "ad_spend": Column(float, Check.ge(0), nullable=False),
        # Named `ad_revenue` in the aggregate. This is platform-attributed value
        # at conversion time -- NOT CRM closed-won, and NOT account annual
        # revenue. Three different meanings, one word; see README.
        "revenue": Column(float, Check.ge(0), nullable=False),
        "impressions": Column(int, Check.ge(0), nullable=False),
        "clicks": Column(int, Check.ge(0), nullable=False),
        "conversions": Column(int, Check.ge(0), nullable=False),
    },
    checks=[
        # Funnel monotonicity. Nothing in the source enforces this.
        Check(lambda df: (df["clicks"] <= df["impressions"]).all(),
              error="clicks exceed impressions"),
        Check(lambda df: (df["conversions"] <= df["clicks"]).all(),
              error="conversions exceed clicks"),
    ],
    strict=False,
    coerce=True,
)

# The CRM is two files, not one. `sector` lives on the account (85 rows);
# `deal_stage` and `close_value` live on the pipeline (8,800 rows). No single
# file carries all three, so a single crm_schema could never validate anything
# that exists on disk -- the join in notebook 01 is what brings them together.
accounts_schema = DataFrameSchema(
    {
        "account": Column(str, nullable=False, unique=True),
        "sector": Column(str, Check.isin(CRM_SECTORS), nullable=False),
        # Account annual revenue. The third distinct meaning of the word in this
        # project, after ads platform-attributed revenue and CRM closed-won.
        "revenue": Column(float, Check.ge(0), nullable=True),
    },
    strict=False,
    coerce=True,
)

pipeline_schema = DataFrameSchema(
    {
        "opportunity_id": Column(str, nullable=False, unique=True),
        "account": Column(str, nullable=True),
        "deal_stage": Column(
            str,
            Check.isin(["Won", "Lost", "Engaging", "Prospecting"]),
            nullable=False,
        ),
        # Blank for deals that have not closed. Nullable here is a statement that
        # missing is legitimate -- unlike `sector`, where missing would be a bug.
        "close_value": Column(float, Check.ge(0), nullable=True),
    },
    strict=False,
    coerce=True,
)


def validate_ads(df):
    return ads_schema.validate(df, lazy=True)


def validate_accounts(df):
    return accounts_schema.validate(df, lazy=True)


def validate_pipeline(df):
    return pipeline_schema.validate(df, lazy=True)


if __name__ == "__main__":
    # Demonstrate the constraints that were missing at the source.
    import pandas as pd

    bad_ads = pd.DataFrame({
        "industry": ["Healthcare", "Helthcare"],  # the failure, reproduced
        "ad_spend": [100.0, 200.0],
        "revenue": [500.0, 900.0],
        "impressions": [1000, 2000],
        "clicks": [50, 90],
        "conversions": [5, 9],
    })
    try:
        validate_ads(bad_ads)
    except pa.errors.SchemaErrors as e:
        print("ads: rejected at load, as it should have been at write:\n")
        print(e.failure_cases[["check", "failure_case"]].to_string(index=False))

    # `technolgy` passes -- it is in the frozen vocabulary. `technology`, the
    # correct spelling, does not. That inversion is the point: once a typo is
    # load-bearing, silently accepting the fix is its own kind of drift.
    bad_accounts = pd.DataFrame({
        "account": ["Acme", "Globex"],
        "sector": ["technolgy", "technology"],
        "revenue": [1000.0, 2000.0],
    })
    try:
        validate_accounts(bad_accounts)
    except pa.errors.SchemaErrors as e:
        print("\naccounts: rejected at load:\n")
        print(e.failure_cases[["check", "failure_case"]].to_string(index=False))

    bad_pipeline = pd.DataFrame({
        "opportunity_id": ["O1", "O2"],
        "account": ["Acme", "Globex"],
        "deal_stage": ["Won", "Closed"],  # not a stage this CRM has
        "close_value": [500.0, None],
    })
    try:
        validate_pipeline(bad_pipeline)
    except pa.errors.SchemaErrors as e:
        print("\npipeline: rejected at load:\n")
        print(e.failure_cases[["check", "failure_case"]].to_string(index=False))
