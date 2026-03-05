## Component Rubric Input Schema (CRIS_v03)
### 1. Purpose
This schema defines the reusable input structure used to generate rubric specifications for analytic components.
The schema captures **component-variant rubric inputs** while assuming that rubric templates supply invariant rubric mechanics such as:
- evaluation rules  
- evidence rules  
- performance level structure  
- canonical boundary logic  
- document structure  
- calibration conventions  
A CRIS document therefore contains the information necessary to define the **semantic content of a rubric** for a specific component.
### 2. Design principles
#### 2.1 Separation of rubric mechanics and rubric semantics
Rubric mechanics (evaluation logic, scoring structure) belong to the template.  
Rubric semantics (dimensions, indicators, and dimension-specific rules) belong to the CRIS document.
#### 2.2 Indicators as first-class entities
Indicators are defined independently from dimensions.  
Indicators may therefore be:
- dimension-specific  
- cross-dimension  
#### 2.3 Explicit mapping between indicators and dimensions
Dimensions never embed indicators directly.  
Dimension satisfaction is determined through a mapping layer.
#### 2.4 Support for cross-dimension indicators
Some indicators evaluate properties of the response as a whole (for example coherence or specificity).  
These indicators are defined once and may function as quality gates during boundary rule evaluation.
#### 2.5 Dimension semantic guidance
Dimensions may optionally define conceptual guidance describing the conceptual space graders should consider when interpreting the dimension.
This guidance is explanatory and does not affect dimension satisfaction logic.
#### 2.6 Dimension-specific boundary triggers
Boundary triggers that depend on the semantic content of a dimension must be defined in CRIS rather than in the rubric template.
This prevents hidden coupling between rubric templates and specific subject matter.
# 3. Schema
```yaml
schema_id: CRIS_v03
component:
  component_id: <string>
  component_label: <string optional>
  component_description: <string optional>
dimensions:
  - dimension_id: <string>
    dimension_label: <string>
    scoring_claim: <text>
    dimension_guidance:
      conceptual_variants:
        - <text optional>
        - <text optional>
indicators:
  - indicator_id: <string>
    indicator_label: <string optional>
    indicator_scope: <enum: dimension | cross_dimension>
    indicator_prompt: <text>
    indicator_notes: <text optional>
indicator_dimension_map:
  - dimension_id: <string>
    required_indicators:
      - <indicator_id>
      - <indicator_id>
cross_dimension_indicators:
  - indicator_id: <string>
    gate_role: <enum: quality_gate | informational>
    applies_to_dimensions:
      - <dimension_id>
      - <dimension_id>
    notes: <text optional>
dimension_boundary_triggers:
  approaching_to_below:
    - dimension_id: <string>
      triggers:
        - <text>
  exceeds_to_meets:
    - dimension_id: <string>
      triggers:
        - <text optional>
boundary_rule_params:
  performance_level_labels:
    - <string>
    - <string>
    - <string>
    - <string>
    - <string>
  exceeds:
    required_dimensions:
      - <dimension_id>
    required_cross_dimension_indicators:
      - <indicator_id>
    requires_indicator:
      - <indicator_id optional>
    examples:
      - <text optional>
  meets:
    required_dimensions:
      - <dimension_id>
    required_cross_dimension_indicators:
      - <indicator_id optional>
    additional_constraints: <text optional>
  approaching:
    rules: <text optional>
  below:
    rules: <text optional>
  not_demonstrated:
    rules: <text optional>
hardest_boundary_rule:
  boundary_label: <string>
  condition: <text>
```
# 4. Field descriptions
### 4.1 component
Defines the analytic component to which the rubric applies.
`component_id` should match the identifier used in grading pipelines and rubric specification documents.
Optional fields provide descriptive metadata.
### 4.2 dimensions
Defines the rubric dimensions for the component.
Fields:
- `dimension_id`  
  Unique identifier referenced throughout the rubric.
- `dimension_label`  
  Human-readable name of the dimension.
- `scoring_claim`  
  The evaluative claim describing what graders assess.
- `dimension_guidance` (optional)  
  Conceptual guidance helping graders interpret the dimension’s conceptual scope.
This section generates the **dimension registry** in the rubric specification.
### 4.3 indicators
Defines observable evaluation tests applied to responses.
Fields:
- `indicator_id`  
  Unique identifier.
- `indicator_scope`  
  Indicates whether the indicator applies to a specific dimension or to the response as a whole.
- `indicator_prompt`  
  The evaluation question used by graders.
- `indicator_notes` (optional)  
  Additional clarification.
Indicators will later be grouped into dimension sections using the mapping layer.
### 4.4 indicator_dimension_map
Defines how indicators determine whether a dimension is satisfied.
For each dimension:
- `dimension_id`
- `required_indicators`
All listed indicators must be satisfied for the dimension to count as satisfied during rubric evaluation.
This mapping generates the **dimension satisfaction rule** in the rubric specification.
### 4.5 cross_dimension_indicators
Declares indicators that evaluate response-level properties rather than dimension-specific content.
Typical examples include:
- coherence
- specificity
- evidentiary grounding
These indicators may function as quality gates during boundary evaluation.
### 4.6 dimension_boundary_triggers
Defines boundary triggers that depend on the semantic content of specific dimensions.
Example uses:
- determining when a dimension collapses into generic or non-professional reasoning
- detecting incomplete articulation of a required conceptual boundary
These triggers are inserted into the appropriate boundary rule sections of the rubric specification.
### 4.7 boundary_rule_params
Defines component-specific parameters used when generating boundary rules.
The rubric template provides the invariant structure of boundary logic; this section supplies component-specific requirements such as:
- required dimensions
- required indicators
- example conditions
### 4.8 hardest_boundary_rule
Defines the decisive boundary separating two performance levels.
Most commonly this governs the **Approaching vs Meets** boundary by requiring that all rubric dimensions be satisfied.
The rubric generator inserts this rule into the final specification.
# 5. Generation notes
A rubric generator should construct rubric specifications by combining:
- invariant rubric templates  
- the CRIS input document  
Typical generation steps:
1. Render the dimension registry from `dimensions`.
2. Render indicator definitions from `indicators`.
3. Construct dimension satisfaction rules using `indicator_dimension_map`.
4. Insert cross-dimension indicator logic from `cross_dimension_indicators`.
5. Insert dimension-specific boundary triggers from `dimension_boundary_triggers`.
6. Generate boundary rules using `boundary_rule_params`.
7. Render the decisive boundary rule from `hardest_boundary_rule`.
The resulting document becomes the **component rubric specification**.
