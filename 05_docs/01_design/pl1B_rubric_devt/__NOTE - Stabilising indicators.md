### why outputs vary despite temperature=0
Even with temperature=0 and top_p=1, **full determinism is not guaranteed**. The variation you are seeing is expected in this kind of task.
### primary causes (in order of impact)
#### 1. borderline semantic thresholds (dominant cause)
Your indicators—especially:
- I13 (mechanism/tool)
- I14 (redistribution)
- I61 / I71 / I81 (manifestation articulation)
require **interpretive judgement over weakly specified boundaries**.
Small internal differences in parsing can flip:
- implicit vs explicit mechanism
- generic vs valid redistribution
- named vs sufficiently articulated manifestation
These are **knife-edge decisions**, so even tiny variation yields different labels.
This matches your pattern:
- high stability: I11, I12 (clear, structural)
- lower stability: I13, I14, I61 (interpretive, thresholded)
#### 2. non-determinism in model inference
Even at temperature=0, outputs can vary due to:
- parallelism / batching differences
- floating-point nondeterminism across hardware
- token tie-breaking when probabilities are extremely close
This typically affects **borderline tokens**, which then cascade into different reasoning paths.
#### 3. prompt under-specification for binary decisions
If your scoring prompt allows:
- multiple valid reasoning paths
- soft language like “valid”, “clearly”, “sufficient”
then the model may:
- **reconstruct the rule slightly differently each run**
- especially for mid-level indicators
#### 4. latent ambiguity in indicator definitions
Examples from your set:
- what counts as a “valid mechanism” vs context?
- when is redistribution “expressed” vs implied?
- what qualifies as “articulated”?
If these are not **operationalised as hard tests**, drift occurs.
#### 5. absence of forced decision procedure
If the model is not required to:
- explicitly enumerate candidates
- apply ordered tests
- justify exclusion
then it may:
- shortcut differently across runs
### evidence in your results
Most volatile indicators:

|**indicator**|**iter01**|**iter02**|**delta**|
|---|---|---|---|
|I14|73.3%|86.7%|+13.4|
|I61|46.7%|53.3%|+6.6|
|I25|80.0%|73.3%|-6.7|
These are all **interpretive boundary indicators**, not structural ones.
### what this implies about your system
Your pipeline is:
- **structurally sound** (I11/I12 stable)
- **semantically under-constrained** at mid-layers
This is typical of:
> “human-verifiable but not machine-stable” indicator design

### how to stabilise (concrete actions)
#### 1. convert indicators into decision procedures
Example transformation:
Instead of:
> “valid mechanism or tool identified”

Use:
```
Step 1: extract noun phrases following “through”, “via”, “using”
Step 2: check if phrase refers to:
  - named system, tool, or process
Step 3: reject if:
  - abstract (e.g., “process”, “system” alone)
  - outcome description
Return present/not_present
```
#### 2. enforce extraction before classification
Require model to output:
- detected demands
- detected mechanisms
- detected redistribution phrases
Then classify.
This removes variability from **implicit detection**.
#### 3. add negative constraints explicitly
E.g.:
- “Do not infer mechanism from outcome description”
- “Do not treat ‘review’ as a workflow stage unless qualified”
#### 4. collapse borderline indicators (if needed)
If stability is critical:
- merge I14 + I61
- or redefine I61 as stricter (binary threshold)
#### 5. use self-consistency voting (practical fix)
Run same prompt 3× and:
- take majority vote per indicator
This dramatically reduces variance for borderline cases.
### bottom line
You are not seeing randomness in the usual sense.
You are seeing:
> **deterministic instability at semantic thresholds due to under-specified decision rules**

The fix is not parameter tuning—it is **tightening the indicator operationalisation into explicit procedures**.
If you want, I can rewrite one of your unstable indicators (e.g., I61) into a fully deterministic decision protocol.
