### Note — Repositioning Layer 1 SBO Value Derivation for Human Verification
#### Clarification — Two classes of indicators in Layer 1
Layer 1 must include **two distinct classes of indicators**, both operating under binary verification but differing in the structure they detect.
##### Class A — Core analytic structure indicators (saturating)
These indicators detect **minimal viable analytic structure** required to meet expectations.
Properties:
- fire for most competent responses
- correspond to **baseline task completion**
- typically include:
  - site identification
  - output identification
  - basic linkage
- expected to **saturate** among responses at or above “meets expectations”
Verification characteristics:
- evidence is **direct, localisable, and low-ambiguity**
- decisions are fast and highly consistent across graders
##### Class B — Advanced structural indicators (non-saturating)
These indicators detect **structures that typically appear only in stronger or exceptional responses**.
Properties:
- do **not** fire for baseline competent responses
- correspond to **expanded or enriched analytic structure**
- differentiate:
  - “meets expectations” vs “exceeds expectations”
- must still be:
  - atomic
  - textually grounded
  - independently verifiable
Verification characteristics:
- evidence may be:
  - **distributed across multiple parts of the response**
  - **structurally more complex**
- but must still be:
  - **explicitly present in the text**
  - **defensible through identifiable evidence**
- must **not require holistic judgement or quality assessment**
Constraint:
> Advanced indicators must detect **additional structure**, not **degree or quality of the same structure**.

Not allowed:
- “more detailed explanation”
- “stronger reasoning”
- “more developed answer”
Allowed:
- additional distinct elements
- multiple instances
- explicitly extended structures
#### Purpose of this shift
Layer 1 SBO value derivation is being repositioned to support a **human verification workflow**, rather than a fully expressive analytic evaluation.
The goal is not to capture the full nuance of student performance at this stage, but to enable:
- **fast, reliable human validation**
- **consistent interpretation across graders**
- **low cognitive overhead at scale**
- **clean downstream aggregation into indicators and dimensions**
Layer 1 should therefore function as a **signal detection layer**, not an evaluative layer.
#### What Layer 1 SBO values now represent
Each SBO value should answer a tightly bounded question:
> **Is there sufficient, explicit textual evidence that this analytic signal is present?**

This reframes Layer 1 from:
- “how well is this done?”
to:
- “is this meaningfully present in the response text?”
This applies to **both core and advanced indicators**.
#### Implications for SBO construction
SBOs should now be:
- **atomic** (one signal per SBO)
- **textually verifiable** (grounded in observable phrasing or structure)
- **non-interpretive** (avoid inference about intent or quality)
- **independent** (each SBO stands alone for verification)
Avoid SBOs that require:
- holistic judgement
- comparative evaluation
- interpretation of “strength” or “quality”
Additional constraint for advanced indicators:
- must be verifiable through:
  - identifiable structural elements
  - countable or distinguishable features where applicable
- must not rely on:
  - overall impression
  - perceived sophistication
#### Binary decision rule
Layer 1 operates using a **binary verification scale**:
- 1 = clear, sufficient, explicit evidence
- 0 = absent OR insufficient OR ambiguous
This applies equally to:
- core indicators
- advanced indicators
Interpretation rule:
- “partial”, “weak”, or “implicit” signals → **not present**
- presence requires **recognisable structure**, not keyword mention
#### Evidence and defensibility standard
For any indicator (core or advanced), a TA must be able to:
```text
identify and reference specific parts of the response that demonstrate the signal
```
Evidence may be:
- localised (single span), or
- distributed (multiple spans)
But must be:
- explicit
- identifiable
- non-ambiguous
Not acceptable:
- “overall this seems sufficient”
- “this feels well developed”
Acceptable:
- pointing to concrete elements in the text that instantiate the structure
#### Recommendation for your system
Use binary at Layer 1, with a constrained interpretation rule.
Push nuance into:
- **pattern discovery (Stage 0.3)**
- **indicator design (Class A vs Class B separation)**
- **dimension-level aggregation (Layer 2+)**
This keeps Layer 1:
- fast
- stable
- scalable
- analytically clean
#### Critical design safeguard
Define:
> **“sufficient evidence” = recognisable structural presence, not mere mention**

Otherwise:
- weak signals will be marked as present
- indicators will saturate prematurely
- downstream differentiation will collapse
#### Summary
- Layer 1 is a **verification layer**, not an evaluation layer
- Indicators are divided into:
  - **core (saturating)** signals
  - **advanced (non-saturating)** signals
- All indicators:
  - operate under binary verification
  - require explicit textual evidence
- Advanced indicators:
  - detect additional structure
  - not degree or quality
- Nuance is recovered through:
  - multi-indicator configurations
  - higher-layer aggregation
# KNOCK ON EFFECTS
### 1) Pressure shifts upstream → Stage 0.3 becomes load-bearing
Stage 0.3 must:
- distinguish:
  - baseline structures
  - extended structures
  - incorrect or misleading forms
Otherwise:
- advanced indicators cannot be constructed cleanly
### 2) Indicator design becomes more critical (Stage 1)
Indicators must:
- encode **structural presence**
- separate:
  - minimal vs extended configurations
Failure leads to:
- saturation
- loss of discriminative power
### 3) Information compression at Layer 1 → expansion at Layer 2+
Nuance is reconstructed via:
- combinations of indicators
- presence/absence patterns across signals
### 4) Calibration dynamics change
Binary reduces:
- time
- ambiguity
But requires:
- **clear threshold examples**, especially for advanced indicators
### 5) Error profile changes
Errors become:
- false positives (weak signals marked present)
- false negatives (valid but subtle signals missed)
System sensitivity increases to:
- indicator phrasing
- threshold clarity
### 6) Loss of partial credit is intentional
Partial performance must be represented through:
- **absence of advanced indicators**
- not intermediate values
### 7) Data properties improve
Binary indicators produce:
- cleaner data
- stronger inter-rater reliability
- better downstream modelling properties
### Bottom line
Layer 1 must simultaneously support:
- **baseline verification (core indicators)**
- **high-end discrimination (advanced indicators)**
Both must remain:
- binary
- explicit
- structurally grounded
- human-verifiable without interpretive judgement
