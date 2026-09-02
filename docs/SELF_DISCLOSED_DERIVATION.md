# Deriving revenue from what tribes say about themselves

*Elijah, 2026-08-07:*

> "shakopee — they could say they give x% of gaming revenue to charity and they
> have annual reports and how much they give. i think stuff like that on tribes'
> pages could also be a potential source. they are basically saying how much they
> earn if you link a couple things together."

Correct, and it is the **same arithmetic as compact-derived revenue**, applied to
a source the federal record cannot reach.

```
compact:   payment to state / stated rate            = revenue base
self-disc: charitable giving / stated % commitment   = revenue base
```

Both are division against a rate the party itself published. Neither is a model.

**Why it matters here specifically:** Minnesota compacts carry no revenue
sharing, so there is no state payment to invert — the compact parse returned
**zero** structured revenue terms for Minnesota. Tribal governments are also
outside the 990 universe under IRC §7871, so there is no Form 990. Self-
disclosure is the **only** channel left for a tribe like Shakopee, and it is a
channel the tribe controls and therefore maintains.

---

## THE TRAP THAT DECIDES WHETHER IT PUBLISHES

Almost every real-world commitment is a **floor**, not an equality:

> "at least 5% of net revenues"  ·  "a minimum of"  ·  "more than $400 million"

Divide a floor by a floor and you get a **bound**, not a value. Concretely:

```
gave $400M under a "at least 5%" commitment
    ->  revenue >= $8B          NOT  revenue == $8B
```

So the default output of this method is `BOUNDED_DERIVED_REVENUE` with an
explicit `bound_basis`, and it only reaches `EXACT_DERIVED_PROPERTY_REVENUE`
where the tribe states an **exact rate against a defined base** and an **exact
amount for the same period**. That is rare and must be verified word by word.

Four further checks before any number is recorded:

1. **What base?** Gross gaming revenue, net revenue, net *win*, or profit after
   expenses? These differ by an order of magnitude. Record `revenue_concept`
   verbatim, exactly as the compact layer does.
2. **What period?** A cumulative "more than $400 million since 1996" divided by
   an annual rate is meaningless. Match the period on both sides or refuse.
3. **Whose revenue?** A tribe with several enterprises may compute a commitment
   on gaming only, or on all tribal revenue. A gaming-only rate applied to a
   whole-tribe figure is wrong in both directions.
4. **Is the rate a policy or a requirement?** A voluntary policy can change
   silently between years; a charter or ordinance provision cannot. Prefer the
   latter and date the former.

---

## Where the paired facts live

The method needs **two** quoted facts from the same period. Sources that
routinely carry both:

- **Tribal annual reports and community-impact reports** — often state a giving
  policy and a total in the same document, which is the ideal case.
- **Tribal charitable foundations** — several tribes fund a separate 501(c)(3)
  that *does* file a 990, even though the tribe does not. The foundation's
  revenue is the tribe's contribution, and it is audited.
- **Bond official statements (MSRB EMMA)** — audited, legally consequential.
  **11 of our 29 tribal bond issuances are Seminole.**
- **State charitable-solicitation registrations** where a tribal foundation
  registers.
- **Local government agreements** — impact payments computed as a percentage.
- **Press releases** stating a cumulative total, useful only for a bound.

---

## How it is stored

Same schema as the compact derivation, so the two are comparable and neither
looks stronger than it is:

```
measurement_status   EXACT_DERIVED_FROM_SELF_DISCLOSED_RATE   (rare)
                     BOUNDED_DERIVED_REVENUE                  (usual)
revenue_concept      verbatim from the source
bound_basis          "commitment stated as a minimum"
rate_source_quote    verbatim + URL
amount_source_quote  verbatim + URL
period               must match on both sides
```

**Two quotes or it does not exist.** A rate without an amount, or an amount
without a rate, is not a derivation.

---

## Why this is worth building

It is the only revenue channel that works where the others structurally fail —
no compact revenue share, no 990, no state regulator publishing per-property
figures. And it is **self-maintaining**: tribes publish these reports annually
because they want the giving known.

It also inverts the philanthropy finding. When Shakopee and San Manuel were
unreachable from the funder side (ProPublica returns 404 — they are not in the
990 universe), the answer was to read recipients. Here the tribe's *own*
statement about giving becomes evidence about the tribe's *revenue*. The
disclosure a tribe makes for reputational reasons is the disclosure the federal
record never required.
