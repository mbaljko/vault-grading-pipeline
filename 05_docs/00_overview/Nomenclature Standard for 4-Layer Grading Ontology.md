## Nomenclature Standard for 4-Layer Ontology
version: v.4
### Purpose
This document establishes the authoritative terminology used throughout the `vault-grading-pipeline`.

### Nomenclature

**Assessment Artefact (AA)**: the portion of a student's submission from which evidence is examined for scoring one or more SBOs.

**Score-Bearing Object (SBO)**: an analytic entity that receives a score derived from evidence drawn from a particular AA.

I am deliberatively not using the term **grading unit**, since it often can mean either "A grading unit is the specific entity that receives a score" or "the thing being graded"

### Conceptual Framework

|         | SBO          | name for the score given to the SBO | Way we refer to each SBO                                                                                                                        | Example SBO     | scale type for the SBO | Name of the scale for this SBO | Values of the SBO scale                                                                                            | Summary: AA specification per layer     |
| ------- | ------------ | ----------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------- | --------------- | ---------------------- | ------------------------------ | ------------------------------------------------------------------------------------------------------------------ | --------------------------------------- |
| Layer 1 | `indicator`  | `indicator_score`                   | `[I\|P]_sid_cid_iid` where:<br>`sid` = submission identifier<br>`cid` = component identifier<br>`iid` = indicator identifier (\[I,P\]\[0-9\]*)  | `I_PPP_SecA_I1` | evidence               | `indicator_evidence_scale`     | `evidence`, `partial_evidence`, `little_to_no_evidence`                                                            | a component of the student's submission |
| Layer 2 | `dimension`  | `dimension_score`                   | `[D\|Q]_sid_cid_did` where:<br>`sid` = submission identifier<br>`cid` = component identifier<br>`did` = dimension identifier (\[D\|Q\]\[0-9\]*) | `D_PPP_SecA_D1` | evidence               | `dimension_evidence_scale`     | `demonstrated`, `partially_demonstrated`, `little_to_no_demonstration`                                             | a component of the student's submission |
| Layer 3 | `component`  | `component_score`                   | `C_sid_cid` where:<br>`sid` = submission identifier<br>`cid` = component identifier (short string)                                              | `C_PPP_SecA`    | performance            | `component_performance_scale`  | `exceeds_expectations`, `meets_expectations`, `approaching_expectations`, `below_expectations`, `not_demonstrated` | a component of the student's submission |
| Layer 4 | `submission` | `submission_score`                  | `S_sid` where `sid` is the submission identifier (short string), determined by course's assessment architecture document                        | `S_PPP`         | performance            | `submission_performance_scale` | `exceeds_expectations`, `meets_expectations`, `approaching_expectations`, `below_expectations`, `not_demonstrated` | the student's entire submission         |


### Scoring Passes
There are 4 scoring passes to the grading pipeline:
- Layer 1: scoring of a set of multiple `indicator` 
- Layer 2: scoring of a set of multiple `dimension` (there are different 'kinds', explained below)
- Layer 3: scoring of a set of multiple `component`
- Layer 4: scoring of a set of multiple `submissions` (one `submission` for every student) 

### Layering
#### Layer 1
- AA: each `submission_id × component_id` from the canonical population
- SBOs: various `I_sid_cid_iid` (or may be denoted `P_sid_cid_iid`)
- Result: each student will have many, many `[I|P]_sid_cid_iid` scores.
##### Layer 1 scoring logic: 
- the score for each `[I|P]_sid_cid_iid` is determined by evidence found in the relevant AA
- some `[I|P]_sid_cid_iid` may be "dimension-tailored" (meaning they are attuned to a specific aspect of the component, which we will later call a `dimension`)
- some `[I|P]_sid_cid_iid` may be "holistic" (meaning that they look at the component as a whole, e.g., grammar, clarity, the presence of a concrete example)
- we don't need to formally signal their category, it will be implicitly encoded by the mapping relationship expressed in the next level
#### Layer 2
- AA: each `submission_id × component_id` from the canonical population
- SBOs: various `D_sid_cid_did`
- Result: each student will have many `D_sid_cid_did` scores, fewer than `[I|P]_sid_cid_iid` scores.
##### Layer 2 scoring logic:  
- in general, the score for each `[D|Q]_sid_cid_did` is determined from the pool of evidence represented in the set of `[I|P]_sid_cid_iid` scores
- specifically, the score for each `[D|Q]_sid_cid_did` is determined by a mapping table that expresses the combination of `indicator_score` values for certain `[I|P]_sid_cid_iid` that determine that particular `dimension_score`
	- "tailored" dimensions: most `[D|Q]_sid_cid_did` will combine two or more "dimension-tailored"  `[I|P]_sid_cid_iid`. 
		- In this case, the dimension will tend to be labelled `D_sid_cid_did` as opposed to `Q_sid_cid_did`,  The use of `D` vs `Q` is simply an information convention and will not be enforced.
		- In this case, the indicator will tend to be labelled `I_sid_cid_iid` as opposed to `P_sid_cid_iid`.  The use of `I` vs `P` is simply an information convention and will not be enforced.
	- "pan-component" dimensions: some `[D|Q]_sid_cid_did` are derived from a single "holistic" indicator `[I|P]_sid_cid_iid`
		- In this case, the dimension will tend to be labelled `Q_sid_cid_did` as opposed to `D_sid_cid_did`,  The use of `D` vs `Q` is simply an information convention and will not be enforced.
		- In this case, the indicator will tend to be labelled `P_sid_cid_iid` as opposed to `I_sid_cid_iid`.  The use of `I` vs `P` is simply an information convention and will not be enforced.
		- in the past I have referred to these as "cross-dimensional", even though they are dimensions themselves. The cross-dimensionality happens at the indicator level. So, strictly speaking, this is inconsistent nomenclature
		- It is better to refer to these dimensions as "pan-component dimensions" (rather than "cross-dimensional" dimensions).
#### Layer 3
- AA: each `submission_id × component_id` from the canonical population
- SBOs: various `C_sid_cid`, one for each component of the assignment
- Result: each student will have several `C_sid_cid` scores, fewer than `D_sid_cid_did` scores
##### Layer 3 scoring logic:
- in general, the score for each `C_sid_cid` is determined from the pool of evidence represented in the set of `D_sid_cid_did` scores
- specifically, the score for each `C_sid_cid` is determined by a mapping table that expresses the combination of `dimension_score` values that determine the `component_score`
- the "tailored" and "pan-component" dimensions combine to produce a derived `component_score`

#### Layer 4
- AA: each `submission_id` from the canonical population
- SBO: one, which is `S_sid`
- Result: each student will have one `S_sid` score
##### Layer 4 scoring logic:
- in general, the score for each `S_sid` is determined from the pool of evidence represented in the set of `C_sid_cid` scores
- specifically, the score for each `S_sid` is determined by a mapping table that expresses the combination of `component_score` values that determine the `submission_score` value
- cross-component scoring, if used, can happen only at Layer 4

This nomenclature is normative. All future artefacts must conform to it.

### Scoring Flow Invariant

Across all layers of the grading pipeline, scores are derived according to the following invariant:

1. Evidence is examined within a defined Assessment Artefact (AA).
2. One or more Score-Bearing Objects (SBOs) associated with that AA are assigned scores.
3. Higher-layer SBO scores are derived only from lower-layer SBO scores through explicit mapping tables.

Formally:

AA → indicator SBO scores → dimension SBO scores → component SBO scores → submission SBO score

The AA defines the evidence boundary for a scoring pass, while SBOs define the analytic entities that receive scores derived from that evidence.

### Implementation Notes
- Implementation issue for Layer 3
	- Layer 3 depends on representation in the canonical population
	- moodle database export provisions for several discrete per-student elements in the export of the student submissions, this is what I am calling a component
	- if the moodle export produces one item per student, then this would result in one component.  If one wanted to break that into chunks, then there would need to be a segmentation stage
	- this stage relies on the ability to convert into "long format" 
	- Limitation:  no way to do pan-component scoring even in a multiple-component submission content with this architecture.  If this is desired, would need to introduce a placeholder component

### AA specification per layer

| **Layer** | **AA**                 |
| --------- | ---------------------- |
| 1         | submission × component |
| 2         | submission × component |
| 3         | submission × component |
| 4         | submission             |


### Structural Invariants

- (component_id, dimension_id) must be unique
- every component defines its dimensions
- exactly one score per SBO instance


### File Naming

Prefixes

L1_SBO_indicators
L2_SBO_dimensions
L3_SBO_components
L4_SBO_submissions

`CAL_<sid>_<cid>`

`CAL` or `PROD` for calibration or production

`<sid>` submission id

`<cid>` component id

