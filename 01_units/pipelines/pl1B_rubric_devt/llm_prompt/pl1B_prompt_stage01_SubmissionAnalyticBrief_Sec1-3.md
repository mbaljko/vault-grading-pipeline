# .
```
BEGIN GENERATION
```

supply this prompt not only with the payload spec, but also the student-facing assignment materials

# . 
````
## PROMPT: Stage 0.1 produce a submission analytic brief

Before constructing indicators and dimensions, the analytic goals of the **entire submission** must be clarified.

### Purpose of this stage
This stage produces an interpretive specification of the assignment as a whole, suitable for downstream rubric construction. The brief must do more than list components. It must explain the analytic purpose of the submission, the conceptual progression across components, the kinds of engagement each component is designed to elicit, and the initial meaning of score labels at the component level where supported by the input.

### Input
```
<ASSESSMENT_ID>_AssignmentPayloadSpec_v01
<ASSESSMENT_ID>_AssignmentMaterials (student-facing prompts, instructions, and description)
```
Input interpretation rules:

- The Assignment Payload Specification defines the **structural contract** of the submission (components, identifiers, evidence surfaces).
- The Assignment Materials define the **conceptual intent and analytic expectations** of the assignment.

The analytic brief must be constructed by:
- using the payload specification to determine **component structure and boundaries**
- using the assignment materials to determine **analytic purpose, conceptual claims, and expected reasoning**

Where there is a mismatch:
- prioritise the payload specification for structure
- prioritise the assignment materials for interpretation
  
The model must not rely solely on the payload specification when assignment materials are provided. Outputs that only restate structural information without incorporating conceptual intent from the assignment materials are not valid.

From this input produce a **submission analytic brief**.

The analytic brief must describe:
- the analytic goals of the assignment as a whole
- the conceptual claims, forms of understanding, or interpretive work students are expected to produce
- the intellectual structure and progression of the submission
- the role played by each component of the submission
- the initial grading interpretation of each component, where supported by the input

### Deliverable
Produce the following document:
```
<ASSESSMENT_ID>_SubmissionAnalyticBrief_v01.md
```

### Required top-level sections

| section | required content |
|---|---|
| Overview — Analytic Goals and Conceptual Claims | the overall analytic purpose of the assignment, the kind of intellectual work students are being asked to perform, the conceptual claims or forms of understanding the submission is intended to surface, the intellectual progression across components, and where supported by the input, what the rubric is and is not intended to evaluate. **Where the assignment is diagnostic, interpretive, or baseline-setting, the Overview must explicitly name that function and distinguish what the assignment is not intended to do.** |
| Components | analytic interpretation of each assignment component defined in the Component Registry |
| Conceptual Structure of the Submission | synthesis of the conceptual progression across components, including a compact mapping of conceptual dimension to component and a statement of what the submission produces as a whole |

### Component subsection requirements

Within the **Components** section, the document must contain one subsection for **each `component_id` defined in the Component Registry** of:
```
<ASSESSMENT_ID>_AssignmentPayloadSpec_v01
```

Each component subsection must contain the following subsections:

| subsection content | description |
|---|---|
| Analytic purpose | the conceptual purpose of the component within the submission |
| Indicators of engagement with the analytic or positioning dimension | observable forms of discussion, articulation, reasoning, or interpretive work that would indicate engagement with the component task |
| Initial meanings for scoring labels | an initial interpretation of how score labels apply to this component, using the score labels already established for the assignment if available |

If no authoritative score-label set is available in the input, omit the “Initial meanings for scoring labels” subsection rather than inventing one.

### Scoring-label table format

Where a score-label scale is available, the “Initial meanings for scoring labels” subsection must use the following table structure:

| score_label | template text | interpretation for Section X |
|---|---|---|

The third column must be populated with component-specific meaning.

### Conceptual Structure section requirements

The **Conceptual Structure of the Submission** section must:
- synthesise the progression across components
- provide a compact mapping table of conceptual dimension to component
- state what the submission produces when taken as a whole
- where reasonably supported by the input, indicate how the assignment fits into the broader course arc

### Output style requirements

- Write in structured, moderately elaborated prose rather than terse summary statements.
- Use assignment-level interpretive language.
- Make the document readable as a downstream design artefact for rubric construction.
- Each component subsection must contain enough detail to support later construction of indicators and score interpretations.
- Avoid generic placeholder wording unless no more specific interpretation is supported by the input.
- The brief must read as an interpretive specification, not a minimal schema summary.

### Inference rule

The model may interpret the conceptual role of each component from the assignment payload specification and assignment structure, but must not invent assignment purposes, scoring scales, or component functions that are not reasonably supported by the input. When details are unavailable, the brief should remain specific but non-speculative.

### Required structural form

```
### 1. Overview — Analytic Goals and Conceptual Claims
### 2. Components
#### 2.1 Component: <component_id_1>
##### Analytic purpose
##### Indicators of engagement with the analytic or positioning dimension
##### Initial meanings for scoring labels
#### 2.2 Component: <component_id_2>
##### Analytic purpose
##### Indicators of engagement with the analytic or positioning dimension
##### Initial meanings for scoring labels
   ...
#### 2.n Component: <component_id_n>
##### Analytic purpose
##### Indicators of engagement with the analytic or positioning dimension
##### Initial meanings for scoring labels
### 3. Conceptual Structure of the Submission
```

The set of component subsections must correspond exactly to the component identifiers defined in:
```
<ASSESSMENT_ID>_AssignmentPayloadSpec_v01
```
===
````
