# .
```
BEGIN GENERATION
```



# . 
````
## PROMPT: Stage 0.1 produce a submission analytic brief

Before constructing indicators and dimensions, the analytic goals of the **entire submission** must be clarified.
Input:
```
<ASSESSMENT_ID>_AssignmentPayloadSpec_v01
```
From this input produce a **submission analytic brief**.
The analytic brief describes:
- the analytic goals of the assignment as a whole
- the conceptual claims students are expected to make
- the intellectual structure of the submission
- the role played by each component of the submission
Example analytic brief structure:

| section | content |
|---|---|
| Overview | analytic goals and conceptual claims |
| Component: SectionAResponse | analytic purpose and expected reasoning |
| Component: SectionBResponse | analytic purpose and expected reasoning |
| Component: SectionCResponse | analytic purpose and expected reasoning |
#### Deliverables
Produce the following document:
```
<ASSESSMENT_ID>_SubmissionAnalyticBrief_v01.md
```
The document must contain the following sections.

| section                                         | required content                                                                                                                       |
| ----------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------- |
| Overview — Analytic Goals and Conceptual Claims | analytic goals of the assignment, conceptual claims students are expected to produce, and the intellectual structure of the submission |
| Components                                      | analytic interpretation of each assignment component defined in the Component Registry                                                 |
| Conceptual Structure of the Submission          |                                                                                                                                        |
Within the **Components** section, the document must contain one subsection for **each `component_id` defined in the Component Registry** of:
```
<ASSESSMENT_ID>_AssignmentPayloadSpec_v01
```
Each component subsection must contain:

| subsection content | description |
|---|---|
| Analytic purpose | the conceptual purpose of the component within the submission |
| Expected reasoning structure | the types of reasoning or positioning moves the component asks the student to perform |
Example structure:
```
1. Overview — Analytic Goals and Conceptual Claims
2. Components
   2.1 Component: <component_id_1>
       Analytic purpose
       Expected reasoning structure
   2.2 Component: <component_id_2>
       Analytic purpose
       Expected reasoning structure
   ...
   2.n Component: <component_id_n>
       Analytic purpose
       Expected reasoning structure
3. Conceptual Structure of the Submission
```
The set of component subsections must correspond exactly to the component identifiers defined in:
```
<ASSESSMENT_ID>_AssignmentPayloadSpec_v01
```
===
````
