# Marketing Attribution & Systems-Integration Analysis

[![CI](https://github.com/sreekar2503/marketing-attribution-project/actions/workflows/ci.yml/badge.svg)](https://github.com/sreekar2503/marketing-attribution-project/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

Connecting ad platform spend to CRM closed revenue — and quantifying why the two systems cannot currently be joined.

---

## Business Question

> "Which ad channels are actually producing revenue?"

A marketing team buys ads across Google, Meta, and TikTok. A sales team tracks deals in a CRM. Leadership wants ad spend tied to closed revenue so budget can follow returns.

Answering this requires joining the two systems. This project establishes that the join **cannot currently be made**, quantifies the gap, diagnoses why, and builds the one fix available at the analysis layer.

## Datasets

| Source | File(s) | Rows | Grain |
|---|---|---|---|
| Global Ads Performance (Google, Meta, TikTok) | `ads_performance.csv` | 1,800 | `date × platform × campaign_type × industry × country` |
| CRM Sales Opportunities | `sales_pipeline.csv`, `accounts.csv`, `products.csv`, `sales_teams.csv` | 8,800 deals / 85 accounts | One sales opportunity |

Ad spend covered: **\$11,108,749**. Closed-won CRM revenue: **\$10,005,534**.

A third dataset (`synthetic_b2b_crm`, 734 companies / 5,234 employees) was evaluated and
**rejected**: its Turkish heavy-industry sectors (aerospace, mining, oil & gas) have near-zero
conceptual overlap with the ads verticals, spend is denominated in ₺ rather than USD, and it
carries no funnel stages or dates. Its clean/noisy record pairs would suit a separate
data-cleaning and fuzzy-matching project.

## Integration Problems Found

| # | Problem | Detail |
|---|---|---|
| 1 | **No shared identifier** | Ads data has no ID column of any kind — no `campaign_id`, `utm_source`, or `customer_id`. It is pre-aggregated by the ad platform before export. |
| 2 | **Industry taxonomies share zero values** | Ads uses 5 product-category verticals (`E-commerce`, `EdTech`, `Fintech`, `Healthcare`, `SaaS`); CRM uses 10 firmographic sectors (`finance`, `medical`, `software`, …). Not one value matches, even case-insensitively. |
| 3 | **Zero date overlap** | Ads covers 2024-01-01→2024-12-30. CRM covers 2016-10-20→2017-12-31. A 2,192-day (~6 year) gap. |
| 4 | **No channel field in CRM** | Deals record who closed them, never where the lead came from. Platform-level attribution is impossible even in principle. |
| 5 | **Grain mismatch** | Aggregate dimension-rows vs. individual deals — the join must happen at a rolled-up level. |
| 6 | **Ads grain is not a strict key** | 12 duplicate dimension combinations exist; rows must be summed, never treated as distinct entities. |

A note on a **non**-problem: 16% of CRM deals have a null `account`, but those nulls sit entirely in `Prospecting`/`Engaging` deals. **Zero** closed deals are affected, so all \$10.0M of won revenue remains attributable. This constrains open-pipeline analysis only.

## Match Rate Finding

Joining `ads.industry` ↔ `accounts.sector` — the only remaining candidate key after eliminating all others:

```
Ads industries:              5
CRM sectors:                 10
Successfully matched:        0

Ad spend matched to CRM:     $0.00 of $11,108,749.09   (0.0%)
CRM revenue matched to ads:  $0.00 of $10,005,534.00   (0.0%)
```

**0% match rate.** 100% of both spend and revenue unreconciled.

The failure is **silent**: `pd.merge` raises no exception. An inner join returns an empty DataFrame; a left join returns the expected 5 rows with every CRM column null. Row-count validation alone would not catch this.

### Cheap fixes ruled out

- **String normalisation** — lowercase, strip, punctuation removal, prefix truncation: **0 matches recovered** across all 4 strategies.
- **Fuzzy matching (`thefuzz`)** — agrees with human judgement on only **1 of 5** values. Critically, the scores don't separate signal from noise: the correct pair (`Fintech`→`finance`) scores 57 while an incorrect one (`EdTech`→`technolgy`) scores 53. No threshold keeps the good match and rejects the bad ones.

The mismatch is **semantic, not orthographic** — `Healthcare` and `medical` mean the same thing and share almost no characters. Edit-distance tools cannot bridge that.

## A Second Disagreement: the same word, two definitions

The 0% match rate is about the *join key*. There is a second failure underneath it that the
match rate hides.

Both systems ship a column called **`revenue`**, and they do not agree:

| | Ad platform | CRM | Ratio |
|---|---|---|---|
| Reported revenue | \$54,183,331 | \$10,005,534 | **5.4x** |
| Reported "successes" | 326,812 conversions | 4,238 won deals | **77x** |
| Implied value per success | \$165.79 | \$2,360.91 | 14.2x |

This is **not** a claim that the ad platform is overstating. The two datasets cover different
periods (see A1) and are independent sources, so the ratio is not a like-for-like audit.

The finding is that **the gap cannot be explained with the data available.** Two systems each
report a figure called revenue, they differ by 5.4x, and there is no field in either system that
reconciles them — no shared definition, no owner of the difference. Ask "what is our revenue?"
and you get two defensible answers an order of magnitude apart with no way to adjudicate.

The 77x gap in event counts is the clearer tell: a platform "conversion" is any tracked action
(form fill, signup, add-to-cart); a "won deal" is a signed contract. Different units, same
dashboards.

**This is the same root cause at a different layer.** The taxonomy mismatch is two vocabularies
for one dimension; this is two definitions for one measure. Both come from the same unowned
seam — and critically, **the crosswalk fixes the first and does nothing for the second.** A
shared reference table has to govern *metric definitions*, not just category values.

## Reconciliation Fix

A hand-built semantic crosswalk mapping ads industries to CRM sectors, shipped as an inspectable
`output/industry_crosswalk.csv` with a confidence level and written rationale per row.

```
Ads categories matched:   0 → 4 of 5   (80%)
Ad spend reconciled:      0.0% → 79.3%   ($8,811,771 of $11,108,749)
CRM revenue reconciled:   0.0% → 52.5%   ($5,255,965 of $10,005,534)
```

| ads `industry` | CRM `sector` | Confidence |
|---|---|---|
| Fintech | finance | High |
| Healthcare | medical | High |
| SaaS | software | High |
| E-commerce | retail | Medium — retail includes accounts no e-commerce campaign would target |
| EdTech | *(none)* | Gap — no CRM counterpart exists |

Coverage is **asymmetric by design**. The CRM describes 10 sectors; the ad platform buys against
5. Most unreconciled CRM revenue comes from parts of the business marketing does not advertise
into (`employment`, `entertainment`, `telecommunications`, `services`) — a finding about the
business, not mapping debt.

### The judgement call, quantified

`technolgy` (misspelled in source) could arguably fold into `SaaS`. The CRM's data dictionary
defines `sector` as **"Industry"** and nothing else — there is no written definition separating
it from `software`, and account names and firmographics provide no discriminating evidence.

It is excluded from the base case and the cost of that choice is measured rather than hidden:

| Scenario | CRM revenue reconciled | Coverage |
|---|---|---|
| Base case (excluded) | \$5,255,965 | 52.5% |
| Alternative (`technolgy` → SaaS) | \$6,771,452 | 67.7% |

**One undocumented sector is worth 15.1 percentage points of coverage** and would more than
double SaaS-mapped revenue. That is the single strongest argument in this project for a governed
reference table: the information needed to settle it does not exist in the data, only in what
someone meant when they typed the word six years ago.

## Root Cause

Each taxonomy is correct for its own purpose. Marketing adopted the ad platform's targeting categories because those are what you buy against. Sales built categories matching how territories are run. Neither team erred.

**The failure is an unowned seam.** No shared reference table, no governance forum, and no one whose performance depends on the two systems agreeing. Both systems have clean internal referential integrity — the problem exists only *between* them, which is why it stays invisible until someone asks a question spanning both.

Only **1 of 5** root causes is fixable in the analysis layer:

| Problem | Layer | Fixable in analysis? | Permanent fix |
|---|---|---|---|
| Taxonomy mismatch | Semantic | **Yes — crosswalk** | Shared reference table, jointly owned |
| No shared identifier | Instrumentation | No | UTM tagging + lead-source capture on forms |
| No channel field in CRM | Schema | No | Mandatory `lead_source` picklist |
| Non-overlapping dates | Process | No | Aligned reporting calendar / shared warehouse |
| Ads pre-aggregated at source | Vendor | No | Server-side conversion API |

## Key Assumptions

- **A1 — Time alignment abandoned, not faked.** CRM dates were *not* re-anchored onto the 2024 calendar. Doing so would manufacture a temporal relationship that doesn't exist. Both sides are treated as cross-sectional totals over their own periods.
- **A2 — Sector as audience proxy.** A `finance`-sector deal is assumed plausibly influenced by `Fintech`-targeted ads. This is an assumption about audience overlap, not causation.
- **A3 — Revenue = `sum(close_value)` where `deal_stage == 'Won'`.**

**This analysis cannot** attribute revenue to a platform, to an individual deal, or measure time-lagged effects. It is descriptive mix comparison only.

## Before vs After Comparison

Denominators are asserted identical across both states before anything is plotted — a coverage
improvement that comes partly from a moved denominator is not an improvement.

| | Before (naive join) | After (crosswalk) | Change |
|---|---|---|---|
| Ads categories matched | 0 of 5 | 4 of 5 | +4 |
| Ad spend reconciled | \$0 (0.0%) | \$8,811,771 (79.3%) | +79.3pp |
| CRM revenue reconciled | \$0 (0.0%) | \$5,255,965 (52.5%) | +52.5pp |
| Still unreconciled | \$11.1M / \$10.0M | \$2.30M / \$4.75M | — |

**Three questions became answerable** (industry mix comparison, cost per closed deal, whether
the two systems agree on revenue per ad dollar). **Four remain blocked** — each needs
instrumentation, schema, or process change, not analysis.

### What the fix exposed

With both systems on one axis, revenue per ad dollar can be computed from each independently:

```
Platform-reported (ads `revenue`):        4.84x
CRM-anchored (closed-won `close_value`):  0.60x
Divergence:                                8.1x
```

This is **not** evidence the ad platform inflates. The two sides cover non-overlapping periods
six years apart and count different events (326,812 conversions vs 4,238 won deals), so neither
figure has a break-even interpretation. What it shows is that two systems inside one
organisation answer *"what did a marketing dollar return?"* with numbers an order of magnitude
apart — and before the crosswalk, that disagreement could not even be stated per-industry,
because no row existed on which both numbers appeared.

Making a disagreement visible is not resolving it. Resolution requires a definition both teams
sign, which is governance, not analysis.

## Recommendation

The crosswalk is a **stopgap**, and it is worth being precise about what kind. It is a static CSV
with no owner that will silently stop being correct the first time either team adds a category —
a new ads vertical, a new CRM sector — and nothing in the pipeline will raise an error when that
happens. The validation in notebook 03 asserts that it covers both vocabularies *as they exist
today*. That check fails loudly after a taxonomy change, which is the desired behaviour, but only
if somebody is running it.

So the correct description of the current state is not *fixed*. It is **measurable, for now**.

Four of the five original root causes, plus the newly exposed metric-definition gap, are
untouched by any analysis. They are fixed at the point data is captured, not the point it is
read:

| Priority | Fix | Addresses | Owner | Effort |
|---|---|---|---|---|
| **1** | Mandatory `lead_source` picklist on lead capture forms, written to the CRM | No channel field; no shared identifier | Sales ops + web | Low — one field, one picklist |
| **2** | A jointly-owned reference table for industry/sector, with a **named owner per value** | Taxonomy mismatch, permanently | Sales ops + marketing ops | Low to build, ongoing to govern |
| **3** | A definition register for shared metrics — what counts as a conversion, what counts as revenue, over what window | The 8.1x revenue divergence | Finance + marketing + sales | Medium — requires agreement, not engineering |
| **4** | UTM tagging on all campaigns, captured at form submission | Deal-level attribution | Marketing ops | Medium |
| **5** | Aligned reporting calendar / shared warehouse | Non-overlapping periods | Data platform | High |

### Why #2 sits above #4 despite being less technically interesting

The strongest evidence in this project for a governed reference table is not the 0% match rate.
It is `technolgy`.

A single CRM sector whose meaning was never written down swings reported coverage by **15.1
percentage points** and more than doubles the revenue attributable to SaaS. The CRM ships a data
dictionary; for the one field this entire analysis depends on, it says *"Industry"* and stops. No
definition, no owner, no examples. The value is also misspelled, which suggests it was free-texted
rather than picked from a governed list.

The analyst cannot resolve that. The information required does not exist in the data — it exists
in whatever someone meant when they typed the word, and that person may no longer work there.
This is not a modelling problem or a tooling problem. Somebody has to **decide it once and write
it down**, which is a governance action that costs almost nothing and that no amount of
engineering substitutes for.

### Why #3 exists at all

Reconciling the taxonomies made the two systems comparable on one axis. It did nothing whatsoever
to make their revenue figures mean the same thing. Mapping `Fintech`→`finance` does not reconcile
\$54.2M against \$10.0M.

A shared reference table that governs only *category values* leaves the larger disagreement in
place. It has to govern **metric definitions** too, or the organisation ends up with two systems
that agree on what an industry is and still disagree about revenue by an order of magnitude.

### What not to do

- **Do not reallocate budget from this analysis.** The mix comparison is descriptive. It says the
  industry composition of spend differs from that of closed revenue; it does not say that moving
  spend would move revenue. That question needs overlapping time periods and a channel field,
  neither of which exists.
- **Do not automate the crosswalk.** Fuzzy matching agreed with human judgement on 1 of 5 values
  and its scores did not separate correct from incorrect (the right answer scored 57, a wrong one
  53). Any threshold-based pipeline would accept four wrong mappings and report no errors.
- **Do not treat 79.3% as a target to push toward 100%.** Most of the residual is business the ad
  platform never targeted. Forcing those values to map would manufacture coverage, not create it.

---

## Limitations

Stated plainly, because a portfolio piece that only lists its strengths is an advertisement.

- **The datasets are synthetic and unrelated.** They were selected to exhibit a realistic
  integration failure, not sampled from one organisation. The `technolgy` misspelling is
  therefore plausibly an artifact of data generation rather than evidence of real organisational
  drift. The *mechanism* it illustrates — an ungoverned free-text field whose meaning nobody
  owns — is real and common; the specific instance is a convenient example of it, and the 15.1pp
  figure should be read as "here is what this class of gap costs," not as a measured finding
  about a real company.
- **The 8.1x revenue divergence is not a like-for-like measurement.** Non-overlapping periods,
  different event definitions. It demonstrates that two systems can disagree by an order of
  magnitude with nothing reconciling them; it does not quantify any real platform's inflation.
- **`E-commerce`→`retail` is Medium confidence and over-attributes** by an unmeasurable amount,
  because the CRM's retail sector contains accounts no e-commerce campaign would target.
- **A2 (sector as audience proxy) is unfalsifiable with this data.** Nothing establishes that any
  ad reached any account.

---

## Status

**Complete.** The business question — *"which ad channels are actually producing revenue?"* — is
answered, and the answer is that it cannot be answered with these systems as they are currently
instrumented. That finding is quantified (\$11.1M of spend, \$10.0M of revenue, 0% reconcilable
at the outset), diagnosed to five root causes, and the one root cause addressable in the analysis
layer has been fixed, validated, and measured (0% → 79.3% of spend, 0% → 52.5% of revenue).

The remaining fixes are organisational and are listed above.

---

## Repo Structure

```
marketing-attribution-project/
├── data/
│   ├── raw/                    # untouched source data
│   │   ├── ads_performance.csv
│   │   └── crm_sales_opps/
│   └── clean/                  # typed/enriched intermediates
├── notebooks/
│   ├── 01_data_profiling.ipynb # profile each system in isolation
│   ├── 02_naive_join.ipynb     # attempt join, quantify 0% match rate
│   ├── 03_reconciliation.ipynb # build + validate the crosswalk, measure recovered coverage
│   └── 04_before_after.ipynb   # before/after comparison, cross-system metrics
├── output/                     # aggregates, baselines, crosswalk, comparisons
├── .gitignore
├── requirements.txt            # pinned to the environment outputs were built in
└── README.md
```

### A note on column naming

`accounts.revenue` is renamed to **`account_revenue`** when the enriched CRM view is built
(notebook 01). Without that rename, notebook 04 would hold three different quantities all called
`revenue`: the account's annual revenue (firmographic), the deal's `close_value`, and the ads
table's platform-reported conversion value. Given that this project exists because two systems
used the same word for different things, letting that happen inside the analysis would be
careless.

## Setup

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Versions are pinned in `requirements.txt` to the environment the committed notebook outputs were
produced in (Python 3.12.3, pandas 3.0.2, numpy 2.4.4). A project about two systems drifting
apart unnoticed should not itself drift.

Run notebooks in order — `01` writes the typed parquet files that `02` reads. `data/clean/` is a
build artifact and is gitignored; notebook 01 regenerates it.

---

## Licence

Code and analysis released under the [MIT Licence](LICENSE).

The two source datasets in `data/raw/` are third-party Kaggle datasets, committed
so the notebooks re-run without a manual download step. They are redistributed
here under their own terms, not under this repository's licence.
