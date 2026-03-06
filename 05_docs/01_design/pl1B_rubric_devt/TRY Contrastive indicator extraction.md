The stronger method is **contrastive indicator extraction**, which is a structured way of discovering indicators by examining **pairs or small sets of responses that differ in analytically meaningful ways**. It is stronger than pattern clustering because it forces the model (and you) to identify the **precise textual signals that distinguish two response types**.
Instead of asking “what patterns exist,” you ask:
> What observable signals distinguish responses that succeed at the analytic task from those that do not?

That produces indicators that are **far more discriminative and operational**, which is exactly what you need for Layer 1 SBO design.
### Conceptual idea
Every indicator should ideally correspond to a **contrastive boundary** in the response space.
Example contrast:

| **Response A** | **Response B** |
|---|---|
| explicitly assigns accountability | describes workflow without assigning responsibility |
The signal that distinguishes them becomes an indicator.
This makes the indicator:
- empirically grounded  
- operationally detectable  
- strongly tied to analytic intent  
### Components with multiple analytic sub-spaces
Some assignment components ask students to perform **multiple distinct analytic moves**. These moves correspond to **analytic sub-spaces** within the response.
For example, a component might require students to address:
```
accountability locus
role boundary and responsibility hand-off
professional obligations
```
In such cases, contrastive extraction should be **anchored to each analytic sub-space separately**, rather than performed across the entire response.
If contrastive extraction is applied globally, the model may surface differences that reflect **general writing quality or style**, rather than signals tied to the analytic tasks of the component.
Instead, perform contrastive extraction **within each analytic sub-space**.
Example structure:
```
Sub-space A — Accountability framing
Sub-space B — Role boundary and responsibility hand-off
Sub-space C — Professional obligations
```
Contrastive pairs are then identified **within each sub-space**, ensuring that the resulting indicators correspond directly to the analytic expectations of the component.
### Step-by-step workflow
#### Step 1 — Select a calibration sample
Same as before:
```
20–40 responses
```
Dataset structure:
```
submission_id
component_id
cleaned_response_text
```
### Step 2 — Identify analytic sub-spaces
Before running contrastive extraction, identify the **analytic sub-spaces implied by the component instructions**.
Example:
```
Sub-space A: accountability locus
Sub-space B: role boundary / responsibility hand-off
Sub-space C: professional obligations
```
These sub-spaces usually correspond to:
- bullet points in the prompt  
- explicit analytic questions  
- distinct conceptual dimensions the student must address  
Contrastive analysis is then performed **separately within each sub-space**.
### Step 3 — Ask the model to find contrastive pairs
Prompt concept:
```
Examine the responses with respect to the following analytic focus:
<analytic sub-space description>
Identify pairs of responses that approach this aspect of the task in
clearly different ways.
For each pair:
- briefly describe how the approaches differ
- quote the language that reveals the difference
```
Example output:
```
Pair 1
Response A assigns responsibility explicitly:
"the engineer remains accountable for safety compliance"
Response B describes the workflow without assigning responsibility:
"the design is reviewed before approval"
Distinguishing signal:
explicit assignment of accountability
```
Another pair might reveal:
```
Pair 2
Response A identifies responsibilities beyond the professional role:
"regulators and manufacturers also share responsibility"
Response B limits responsibility to the professional:
"the engineer must ensure safety"
Distinguishing signal:
recognition of distributed responsibility
```
### Step 4 — Extract contrastive signals
From the contrasts you derive signals like:
```
explicit assignment of accountability
identification of responsibility outside the professional role
description of responsibility hand-off
explicit mention of regulatory oversight
```
These signals become **candidate indicators**.
When sub-spaces are used, signals are first grouped by sub-space:
```
Accountability signals
Role-boundary signals
Professional-obligation signals
```
These groups often later inform **dimension formation in Stage 2**.
### Step 5 — Convert signals into indicator SBO instances
Example:
```
I1 response explicitly assigns accountability to a specific actor
I2 response identifies responsibility outside the professional role
I3 response describes a responsibility hand-off
I4 response identifies regulatory oversight
```
Populate:
```
Rubric Template: 5.4 Layer 1 SBO Instances (Draft)
```
### Step 6 — Build evaluation guidance using contrastive evidence
The contrastive pairs provide **real textual evidence** for designing evaluation guidance.
Example entry for Section 6.1:
```
indicator_definition
response assigns accountability to a specific actor
assessment_guidance
look for explicit assignment language such as
"the engineer is responsible", "ultimate accountability lies with"
evaluation_notes
do not count vague statements such as
"everyone involved should ensure safety"
```
Populate:
```
Rubric Template: 6.1 Layer 1 SBO Value Derivation
```
### Why contrastive extraction is stronger
Simple pattern discovery answers:
```
What patterns exist?
```
Contrastive extraction answers:
```
What signal distinguishes these two responses?
```
Indicators built from contrasts are better because they:
- correspond to **decision boundaries**
- reduce ambiguous detection
- produce clearer evaluation instructions for LLM prompts
### How it fits your rubric pipeline
The calibration sample becomes a **signal discovery engine**.
```
calibration responses
        ↓
anchored contrastive analysis
        ↓
candidate indicators
        ↓
Stage 1 indicator SBO instances
```
When analytic sub-spaces are present, the process becomes:
```
calibration responses
        ↓
sub-space anchored contrasts
        ↓
sub-space signal sets
        ↓
candidate indicators
```
These signals often naturally cluster into **candidate dimensions**, feeding Stage 2.
Example cluster:
```
I1 explicit accountability
I2 distributed responsibility
I3 responsibility transfer
```
These might later form:
```
D1 Accountability framing
```
### Why this method works especially well for LLM grading
LLMs perform best when detection instructions are based on:
```
clear textual contrasts
explicit examples
```
Contrastive extraction produces indicators grounded in **real response language**, which improves reliability during automated scoring.
### The most powerful version (optional)
An advanced variant is **contrastive boundary discovery**, where the model identifies:
```
minimal textual differences that change analytic interpretation
```
This reveals the smallest textual cues that determine how a response should be interpreted, making it particularly effective for building **robust indicator evaluation prompts**.
