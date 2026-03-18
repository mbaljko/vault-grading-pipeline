### Note — Repositioning Layer 1 SBO Value Derivation for Human Verification
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
This aligns with:
- your **explicit-text-only evidence rule**
- the need for **rapid human verification**
- later-stage aggregation into richer structures
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
#### Binary vs triary decision
This is the key design decision.
##### Option 1 — Binary (Present / Not Present)
**Form:**
- 1 = present
- 0 = not present
**Advantages:**
- fastest for human graders
- lowest ambiguity
- highest inter-rater reliability
- clean aggregation downstream
- aligns with “evidence detection” framing
**Risks:**
- forces graders to collapse:
    - partial evidence
    - weak execution
    - ambiguous phrasing
        into either present or not present
This can:
- lose useful signal
- create edge-case inconsistency
##### Option 2 — Triary (Full / Partial / None)
**Form:**
- 2 = clear / full evidence
- 1 = partial / ambiguous evidence
- 0 = no evidence
**Advantages:**
- captures **gradation of evidence**
- preserves more information at Layer 1
- reduces forced decisions in borderline cases
**Risks:**
- slower for graders
- introduces interpretation variance
- “partial” becomes a **catch-all category**
- harder to calibrate consistently across TAs
#### Recommendation for your system
Given your design goals and scale:
**Use binary at Layer 1, with a constrained interpretation rule.**
Specifically:
- 1 = clear, sufficient, explicit evidence
- 0 = absent OR insufficient OR ambiguous
And push all nuance into:
- **pattern discovery (Stage 0.3)**
- **indicator construction (Stage 1)**
- **dimension-level aggregation**
This keeps Layer 1:
- fast
- stable
- easy to train graders on
- aligned with your “explicit evidence only” constraint
#### Critical design safeguard
If you adopt binary, you must define:
> **“sufficient evidence” = a threshold of clarity, not mere mention**

Otherwise graders will:
- mark 1 for very weak signals
- inflate presence rates
- reduce discriminative power downstream
So your SBO prompts should implicitly enforce:
- presence requires **recognisable structure**, not just keywords
- vague or implied signals → 0
#### Summary
- Layer 1 is now a **verification layer**, not an evaluation layer
- SBO values indicate **presence of observable analytic signals**
- Binary decisioning is preferred for:
    - speed
    - reliability
    - pipeline clarity
- Loss of nuance at Layer 1 is intentional and recovered later through:
    - contrastive pattern discovery
    - indicator synthesis
    - dimension construction
If you want, the next step would be to:
- revise your Stage 1 prompt so that it **forces binary-compatible SBO phrasing** and avoids accidental reintroduction of graded language.
# KNOCK ON EFFECTS
### Where the knock-on effects actually show up
You’re right—this shift is not local. Moving Layer 1 to binary changes how **information flows through the entire pipeline**.
The key is that you’re not _losing_ nuance—you’re **relocating it upstream and downstream**. But that only works if those other stages are tightened accordingly.
### 1) Pressure shifts upstream → Stage 0.3 becomes load-bearing
If Layer 1 no longer captures partiality, ambiguity, or gradation, then:
- **Stage 0.3 must explicitly surface those distinctions**
- otherwise they disappear entirely
Concretely, Stage 0.3 now needs to reliably distinguish:
- clear execution patterns
- partial / degraded forms
- structurally incorrect but superficially similar forms
If Stage 0.3 is weak or overly summarising, then:
- your indicators will collapse
- binary SBOs will become blunt and uninformative
So the knock-on effect is:
> Stage 0.3 must become more contrastive, more granular, and more disciplined

### 2) Indicator design becomes more critical (Stage 1)
With binary SBOs:
- indicators can no longer rely on “degree”
- they must encode **recognisable structural presence**
This forces indicators to:
- sharpen boundaries between:
    - present vs not present
- avoid:
    - “emerging”, “developing”, “strong” language
Poorly designed indicators will now:
- produce noisy binary outputs
- increase false positives or false negatives
So the knock-on effect is:
> Indicator construction must become more **structurally precise and threshold-aware**

### 3) Information compression at Layer 1 → expansion at Layer 2+
You are compressing:
- {none, partial, strong} → {0,1}
That means later stages must:
- reconstruct meaningful differentiation via:
    - **combinations of SBOs**
    - **patterns across sub-spaces**
Example shift:
Instead of:
- one triary signal
You now rely on:
- multiple binary signals interacting:
    - e.g., presence of:
        - correct structure
        - correct grounding
        - correct linkage
So the knock-on effect is:
> dimensional richness comes from **configuration**, not single scores

### 4) Calibration dynamics change (human graders)
Binary reduces:
- cognitive load
- time per decision
But it increases sensitivity to:
- **threshold interpretation**
Two graders may differ on:
- what counts as “sufficient evidence”
Without strong calibration:
- disagreement clusters at the boundary
- especially for borderline responses
So the knock-on effect is:
> you need **tight threshold examples**, not scale descriptors

### 5) Error profile changes
With triary, errors look like:
- misclassification within a gradient
With binary, errors become:
- **false positives** (marking weak signals as present)
- **false negatives** (missing subtle but valid signals)
This has implications:
- false positives → inflate performance
- false negatives → penalise competent but minimal responses
So the knock-on effect is:
> your system becomes more sensitive to **indicator phrasing and examples**

### 6) Loss of “partial credit” → must be intentional
You are explicitly removing:
- partial credit at the signal level
That is fine—but only if:
- partiality is still visible elsewhere (Stage 0.3 patterns, multi-SBO configurations)
Otherwise:
- students with emerging competence collapse into “absent”
So the knock-on effect is:
> partial performance must be **represented structurally**, not numerically

### 7) Data properties improve (this is the upside)
This shift also gives you major gains:
- cleaner data for modelling
- easier aggregation
- more stable inter-rater agreement
- better suitability for training classifiers later
Binary SBOs are:
- much easier to operationalise at scale
- more robust to noise
So the trade-off is intentional:
> less nuance per signal, more reliability per system

### What you need to adjust before proceeding
To safely adopt binary Layer 1, ensure:
1. **Stage 0.3 is strong enough**
    - explicitly captures partial / incorrect / edge patterns
2. **Indicators are thresholded**
    - clearly define what counts as “present”
3. **Calibration materials exist**
    - especially for borderline cases
4. **You expect combinatorial reconstruction**
    - nuance emerges from multiple SBOs, not one
### Bottom line
Yes—there are knock-on effects.
But they are not a problem if you treat the shift correctly:
- Layer 1 = **detection (binary, strict, fast)**
- Stage 0.3 = **variation capture (rich, contrastive)**
- Later layers = **reconstruction of nuance (combinatorial)**
If any one of those is weak, the system degrades.
If all three are aligned, the system becomes:
- faster
- more reliable
- more scalable
- and actually _more analytically grounded_ than a triary scheme.
