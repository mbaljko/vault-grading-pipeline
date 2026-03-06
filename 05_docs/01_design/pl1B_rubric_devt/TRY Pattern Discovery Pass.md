The trick is to **use the calibration sample itself to surface response patterns before you design indicators**. Instead of inventing indicators from the assignment prompt alone, you let the responses reveal **how students actually express the analytic signals**.
This dramatically improves indicator design because:
- indicators end up matching **real language patterns**, not idealised ones
- you discover **unexpected response strategies**
- you avoid indicators that detect things **no student actually writes**
Below is the method.
### The idea
Before Stage 1, run a **pattern discovery pass** over a small calibration sample (20–40 responses).
The goal is to identify **contrastive response patterns** that correspond to the analytic properties you care about.
You ask an LLM something like:
> Identify distinct ways students approach this component task.

Then you analyse those patterns and derive indicators from them.
### Step-by-step process
#### Step 1 — Collect a calibration sample
Example dataset:
```
submission_id
component_id
cleaned_response_text
```
Sample size:
```
20–40 responses
```
Enough to capture variation but still easy to inspect.
#### Step 2 — Pattern discovery pass
Run a prompt asking the model to **cluster response strategies**.
Example instruction:
```
Read the following responses to the assignment component.
Identify distinct response patterns or strategies students use
when addressing the task.
For each pattern:
- give a short label
- describe the pattern
- quote example phrases from the responses
```
Output might look like:
```
Pattern A — Explicit accountability framing
Students explicitly state where responsibility resides.
Example language:
"the engineer remains responsible..."
"ultimate accountability lies with..."
Pattern B — Diffuse responsibility framing
Students describe responsibility as shared but do not specify actors.
Example language:
"everyone involved should ensure..."
Pattern C — Procedural description
Students describe steps in the workflow without assigning responsibility.
Example language:
"the process moves from design to review..."
```
#### Step 3 — Extract analytic signals
Now look at the patterns and ask:
```
What observable signals distinguish these patterns?
```
Example signals:
```
explicit assignment of accountability
mention of responsibility outside professional role
description of responsibility transfer
use of vague collective responsibility language
```
These become **candidate indicator signals**.
#### Step 4 — Convert signals into indicator SBO instances
Turn those signals into the **short descriptions used in your rubric template**.
Example:
```
I1 response explicitly assigns accountability to a specific actor
I2 response identifies responsibility outside the professional role
I3 response describes a responsibility hand-off
I4 response uses diffuse collective responsibility language
```
These populate:
```
Rubric Template: 5.4 Layer 1 SBO Instances (Draft)
```
#### Step 5 — Use real phrases to shape evaluation guidance
Because the pattern discovery step surfaces **actual student language**, you can build much better evaluation guidance.
Example:
```
indicator_definition:
response assigns accountability to a specific actor
assessment_guidance:
look for explicit language assigning responsibility,
such as "engineer is responsible", "ultimate accountability lies with"
evaluation_notes:
ignore generic statements like "everyone should ensure safety"
```
These populate:
```
Rubric Template: 6.1 Layer 1 SBO Value Derivation
```
### Why this works so well
Without this step, indicator design often assumes **idealised student behaviour**.
Example imagined indicator:
```
Does the response identify distributed responsibility?
```
But real responses might express that as:
```
"the engineer checks the design but the regulator approves it"
```
Pattern discovery reveals those **actual linguistic forms**.
### The structural benefit in your pipeline
The calibration sample becomes the **empirical grounding layer**:
```
assignment specification
↓
analytic brief
↓
pattern discovery (calibration sample)
↓
candidate indicators
↓
Stage 1 indicator SBO development
```
So indicators emerge from:
```
analytic goals
+ observed response behaviour
```
not from abstract rubric writing.
### The very powerful extension (optional but recommended)
Instead of asking the model for **patterns**, ask it for **contrastive pairs**:
```
Find responses that approach the task in clearly different ways.
Explain what distinguishes them.
```
Contrastive examples are extremely effective for indicator design because they reveal **boundary signals**.
Example:
```
Response A explicitly assigns accountability.
Response B describes the process but avoids assigning responsibility.
```
That difference almost always maps cleanly to a **useful indicator**.
### Why this fits your architecture
It naturally produces seeds for both:
```
Stage 1 → indicators
Stage 2 → candidate dimensions
```
because the patterns often cluster into conceptual themes that later become dimensions.
If you’d like, I can also show you an even stronger version of this method used in rubric design called **contrastive indicator extraction**, which is particularly powerful when you are building indicators for LLM scoring.
