# Can we tell which ads are producing revenue?

**Executive summary — Marketing Attribution & Systems-Integration Analysis**

---

## The short answer

**No — not with the systems as they are set up today.** This is not a gap in the analysis. It is a
gap in what the systems record.

We reviewed **$11.1M of ad spend** and **$10.0M of closed sales revenue** and found that **none of
it could be connected**. Not "some of it" — none. There is no field anywhere in either system that
links a dollar spent to a deal won.

---

## Why not

Five reasons. Only one of them is something an analyst can fix.

| What's wrong | Why it matters |
|---|---|
| **The two teams use different words for the same industries** | Marketing buys ads against "Healthcare." Sales files those same customers under "medical." Not one category name matches. |
| **No tracking code follows a lead into the CRM** | Nothing records where a lead came from. When a deal closes, the source is simply gone. |
| **The CRM has no field for marketing channel** | We cannot say whether a deal came from Google, Meta, or TikTok — the question has no answer to look up. |
| **The two systems cover different years** | Ad data covers 2024. Sales data covers 2016–17. No overlap at all. |
| **Ad data arrives pre-summarised from the platform** | Individual leads are already averaged away before we ever see the file. |

Neither team did anything wrong. Each system is internally correct and well-run. **The problem
lives in the space between them, which nobody owns** — which is exactly why it went unnoticed
until someone asked a question that spanned both.

---

## A second problem we found along the way

Both systems report a number called **"revenue."** They disagree by **5.4x** — $54.2M according to
the ad platform, $10.0M according to the CRM.

The two systems also count "successes" differently: the ad platform counted **326,812
conversions**; the CRM recorded **4,238 won deals**. A "conversion" might be a form fill. A "won
deal" is a signed contract. Both numbers appear on dashboards without that distinction attached.

**Ask "what was our revenue?" and you get two defensible answers an order of magnitude apart,
with nothing in either system to settle which one is right.**

---

## What we fixed

We hand-built a translation table matching marketing's categories to sales' categories, with a
written justification and a confidence level for every single row.

| | Before | After |
|---|---|---|
| Ad spend we can compare against sales | **0%** | **79%** |
| Sales revenue we can compare against ads | **0%** | **53%** |

Three previously unanswerable questions are now answerable. **Four are still blocked** — they need
changes to how data is captured, not more analysis.

**Important:** this makes the two systems *comparable*. It does not make them *connected*. We
still cannot attribute a specific deal to a specific campaign.

---

## What we recommend

| Priority | Action | Who owns it | Effort |
|---|---|---|---|
| **1** | Add a required "How did you hear about us?" field on lead forms, saved to the CRM | Sales ops + web | **Low** |
| **2** | Agree one shared industry list, with a named owner for each value | Sales ops + marketing ops | **Low** |
| **3** | Write down what "conversion" and "revenue" mean, and get finance, marketing and sales to sign it | Finance + marketing + sales | **Medium** |
| **4** | Add campaign tracking codes to all ads, captured on form submission | Marketing ops | **Medium** |
| **5** | Align the reporting calendars across both systems | Data platform | **High** |

**Why #2 ranks so highly despite being unglamorous:** one CRM category — spelled `technolgy`,
misspelled, with no written definition — single-handedly swings our results by **15 percentage
points**, depending on whether we count it as software or not. Nobody can tell us which it should
be, because nobody ever wrote it down. That is a fifteen-point swing caused by an unowned word.
No amount of engineering fixes it. Somebody has to decide it once and record the decision.

---

## Three things not to do

1. **Do not move budget based on this.** It shows that spending and revenue are distributed
   differently across industries. It does not show that moving spend would move revenue.
2. **Do not try to automate the translation table.** We tested automated text-matching: it agreed
   with human judgement on 1 category out of 5, and scored a wrong answer higher than a right one.
   It would produce confident, silent errors.
3. **Do not chase 100% coverage.** Most of the remaining gap is business the company never
   advertised into. Forcing it to match would invent coverage, not create it.

---

*Note: this analysis was built on publicly available synthetic datasets, selected to demonstrate a
realistic systems-integration failure. The mechanisms described are common and real; the specific
figures illustrate what this class of problem costs rather than measuring any actual company.*
