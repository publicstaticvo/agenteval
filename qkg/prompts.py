from config import Config
config = Config.from_yaml("config.yaml")
OPTIONS = ['A', 'B', 'C', 'D', 'E']
EXPAND_OPTIONS = ['A', 'B', 'C', 'D', 'E']
NOT_ANSWERABLE = "F"
# ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J']

KNOWLEDGE = f"""You are a senior research scientist in {config.subject}.

You are analyzing a research paper to extract reusable mechanism units for constructing reasoning-based benchmark questions.

Your task is to extract 3–6 independent mechanism units from the given research paper. A mechanism unit is defined as a localized causal structure that satisfies:
- It has identifiable preconditions.
- It leads to identifiable consequences.
- It can independently fail under specific conditions.
- It does NOT require understanding the entire paper to evaluate.

Mechanism units may include:
- A scientific mechanism
- A modeling assumption
- A structural design choice
- A governing constraint
- An inductive bias
- A theoretical dependency
- A system-level tradeoff

Each mechanism unit must contain:

1. mechanism_unit: 
   A concise description of a single causal or structural principle.

2. requires:
   Explicit assumptions or preconditions required for this mechanism to operate.

3. produces:
   Direct consequences or observable behaviors caused by this mechanism.

4. invariants:
   A structural constraint that must hold whenever the mechanism operates correctly, such that violating it changes the identity of the mechanism. (Not an outcome.)

5. breaks_when:
   Concrete conditions under which the mechanism fails or becomes unreliable.

6. minimal_example:
   A simplified abstract scenario (2–3 sentences) illustrating the mechanism.

Strict rules:
- Do NOT describe the paper’s contributions.
- Do NOT summarize the overall method.
- Do NOT combine multiple mechanisms.
- Each unit must be independently testable.
- Each “breaks_when” must describe a concrete failure scenario, not a vague limitation.

Output JSON only:
```json
{{
  "mechanism_units": [
    {{
      "mechanism_unit": "...",  
      "requires": ["assumption_1", ...],
      "produces": ["behavior_1", ...],
      "invariants": ["constraint_1", ...],
      "breaks_when": ["condition_1", ...],
      "minimal_example": "..."
    }},
    ...
  ]
}}
```
"""

KNOWLEDGE_SCHEMA = {
    "type": "object",
    "required": ["mechanism_units"],
    "properties": {
        "mechanism_units": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["mechanism_unit", "requires", "produces", "invariants", "breaks_when", "minimal_example"],
                "properties": {
                    "mechanism_unit": {"type": "string", "minLength": 1},
                    "requires": {"type": "array", "items": {"type": "string", "minLength": 1}},
                    "produces": {"type": "array", "items": {"type": "string", "minLength": 1}},
                    "invariants": {"type": "array", "items": {"type": "string", "minLength": 1}},
                    "breaks_when": {"type": "array", "items": {"type": "string", "minLength": 1}},
                    "minimal_example": {"type": "string", "minLength": 1}
                },
                "additionalProperties": False
            }
        }
    },
    "additionalProperties": False
}

KNOWLEDGE_FILTER = f"""You are a strict scientific benchmark filter for the subject area: {config.subject}. You are evaluating extracted mechanism units for suitability in reasoning-benchmark construction.

A mechanism unit is expected to contain:
- mechanism_unit
- requires
- invariant
- produces
- breaks_when
- minimal_example

Your task is NOT to judge scientific correctness. Your task is to judge structural suitability for reasoning benchmark construction.

Evaluate the following:

1. Atomicity:
   Does this mechanism describe a single causal principle?

   - atomic:
       A single, well-defined causal mechanism that can be reasoned about independently.
   - composite:
       Multiple mechanisms or loosely connected causal ideas bundled together.
   - vague:
       Descriptive, high-level, or lacks clear causal structure.

2. Explicit invariant presence:
   Does the mechanism clearly specify a structural property (invariant) that must hold whenever the mechanism operates correctly, such that violating it changes the identity of the mechanism?

   - explicit:
       A falsifiable, structural constraint (e.g., monotonic relation, bounded divergence, order consistency).
   - implicit:
       An invariant can be inferred but is not clearly articulated.
   - none:
       No structural invariant; only outcomes or design descriptions are given.

3. Structural perturbability:
   Can at least one of the following be independently modified without logical collapse of the mechanism?

   - requires
   - invariant
   - breaks_when

   (The mechanism should allow meaningful counterfactual variation.)

   Answer:
   - yes
   - no

4. Hidden dependency risk:
   Does understanding or evaluating the mechanism require substantial background knowledge from the original paper or domain-specific assumptions not stated in the mechanism?

   - low:
       Self-contained and structurally evaluable.
   - medium:
       Some domain assumptions required but manageable.
   - high:
       Cannot be evaluated without detailed paper context.

5. Counterfactual coherence:
   If assumptions or invariants are modified, can logically coherent counterfactual scenarios be constructed?

   - low:
       Any modification collapses the mechanism immediately.
   - medium:
       Some modifications possible but fragile.
   - high:
       Multiple stable counterfactual variants possible.

6. Reasoning depth potential:
   Would reasoning about this mechanism naturally require multi-step logical reasoning (e.g., reasoning through invariants, boundary conditions, or causal chains)?

   - low:
       Mostly factual or definitional.
   - medium:
       Requires limited multi-step reasoning.
   - high:
       Requires structured reasoning over causal dependencies.

7. Minimal example quality:

   7.1 Concreteness:
       Does the example contain explicit entities, variables, and observable outcomes?
       - high / medium / low

   7.2 Operational evaluability:
       Can invariant and produces be evaluated using only this example?
       - yes / partial / no

   7.3 Perturbation anchor strength:
       Can the example support meaningful modifications 
       (changing requires, violating invariant, shifting failure boundary)?
       - strong / moderate / weak

Output JSON only:

```json
{{
  "atomicity": "atomic" | "composite" | "vague",
  "explicit_invariant_presence": "explicit" | "implicit" | "none",
  "structural_perturbability": "yes" | "no",
  "hidden_dependency_risk": "low" | "medium" | "high",
  "counterfactual_coherence": "low" | "medium" | "high",
  "reasoning_depth_potential": "low" | "medium" | "high",
  "minimal_example_quality": {{
    "concreteness": "high" | "medium" | "low",
    "operational_evaluability": "yes" | "partial" | "no",
    "perturbation_anchor_strength": "strong" | "moderate" | "weak"
  }}
}}
```
"""

KNOWLEDGE_FILTER_SCHEMA = {
  "type": "object",
  "required": [
    "atomicity",
    "explicit_invariant_presence",
    "structural_perturbability",
    "hidden_dependency_risk",
    "counterfactual_coherence",
    "reasoning_depth_potential",
    "minimal_example_quality"
  ],
  "properties": {
    "atomicity": {"type": "string", "enum": ["atomic", "composite", "vague"]},
    "explicit_invariant_presence": {"type": "string", "enum": ["explicit", "implicit", "none"]},
    "structural_perturbability": {"type": "string", "enum": ["yes", "no"]},
    "hidden_dependency_risk": {"type": "string", "enum": ["low", "medium", "high"]},
    "counterfactual_coherence": {"type": "string", "enum": ["low", "medium", "high"]},
    "reasoning_depth_potential": {"type": "string", "enum": ["low", "medium", "high"]},
    "minimal_example_quality": {
      "type": "object",
      "required": ["concreteness", "operational_evaluability", "perturbation_anchor_strength"],
      "properties": {
        "concreteness": {"type": "string", "enum": ["high", "medium", "low"]},
        "operational_evaluability": {"type": "string", "enum": ["yes", "partial", "no"]},
        "perturbation_anchor_strength": {"type": "string", "enum": ["strong", "moderate", "weak"]}
      }
    }
  }
}

UPGRADE = f"""You are a senior research scientist in {config.subject}. You are performing Mechanism Refinement.

Input:
A structured mechanism unit in JSON format:
{{
  "mechanism_unit": "...",
  "requires": [...],
  "produces": [...],
  "invariants": [...],
  "breaks_when": [...],
  "minimal_example": "..."
}}

Your task:
1. Canonicalize the structure.
2. Convert breaks_when into logically grounded failure_modes.
3. Optionally apply invariant upgrade under strict constraints.
4. Preserve structural identity of the mechanism.

-----------------------------------------
PART A — Canonical Output Structure
-----------------------------------------

Your output format must be JSON only:

{{
  "mechanism_unit": "...",
  "requires": [...],
  "invariants": [...],
  "produces": [...],
  "failure_modes": [
    {{
      "violated_component": "requires" | "invariants",
      "violation_description": "...",
      "original_break_condition": "..."
    }}
  ],
  "minimal_example": "...",
  "upgrade_analysis": {{...}}
}}

-----------------------------------------
PART B — Logical Requirements
-----------------------------------------

1. requires = operational preconditions
2. invariants = structural constraints preserved during correct operation
3. produces = direct observable consequences
4. failure_modes must correspond to violation of requires or invariants
5. No field may introduce new components not implied by the input

-----------------------------------------
PART C — Invariant Upgrade Protocol
-----------------------------------------

You MAY upgrade invariants only.

Definition:

Original:
requires = R
invariants = I

Upgrade:
requires = R (unchanged)
invariants = I' where I' is a strict strengthening of I

-----------------------------------------
Allowed Upgrade Types
-----------------------------------------

1. constraint_strengthening
2. stability_strengthening
3. symmetry_strengthening
4. boundary_explicitization

-----------------------------------------
Forbidden Upgrades
-----------------------------------------

- Changing requires
- Changing produces
- Introducing new functional components
- Altering causal structure
- Introducing new assumptions not implied in input
- Expanding scope beyond original mechanism

If any forbidden change would be required,
DO NOT APPLY upgrade.

-----------------------------------------
Upgrade Output Format
-----------------------------------------

If no upgrade:

"upgrade_analysis": {{
  "upgrade_applied": false
}}

If upgrade applied:

"upgrade_analysis": {{
  "upgrade_applied": true,
  "upgrade_type": "...",
  "original_invariant": "...",
  "upgraded_invariant": "...",
  "monotonicity_justification": "Explain why this preserves mechanism identity."
}}

-----------------------------------------
Critical Structural Constraint
-----------------------------------------

After upgrade:

- requires must be identical to input
- produces must be identical to input
- minimal_example must remain valid
- failure_modes must still correspond to violations

-----------------------------------------
Output Rules
-----------------------------------------

Return only JSON. No commentary and explanation.
"""

FAILURE_MODE_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["violated_component", "violation_description", "original_break_condition"],
    "properties": {
      "violated_component": {"type": "string", "enum": ["requires", "invariants"]},
      "violation_description": {"type": "string", "minLength": 1},
      "original_break_condition": {"type": "string", "minLength": 1}
    }
  }

UPGRADE_SCHEMA = {
  "type": "object",
  "additionalProperties": False,
  "required": ["mechanism_unit", "requires", "invariants", "produces", "failure_modes",
               "minimal_example", "upgrade_analysis"],
  "properties": {
    "mechanism_unit": {"type": "string", "minLength": 1},
    "requires": {"type": "array", "items": {"type": "string", "minLength": 1}},
    "invariants": {"type": "array", "items": {"type": "string", "minLength": 1}},
    "produces": {"type": "array", "items": {"type": "string", "minLength": 1}},
    "failure_modes": {"type": "array", "items": FAILURE_MODE_SCHEMA},
    "minimal_example": {"type": "string", "minLength": 1},
    "upgrade_analysis": {
      "type": "object",
      "additionalProperties": False,
      "required": ["upgrade_applied"],
      "properties": {
        "upgrade_applied": {"type": "boolean"},
        "upgrade_type": {
          "type": "string",
          "enum": [
            "constraint_strengthening",
            "stability_strengthening",
            "symmetry_strengthening",
            "boundary_explicitization"
          ]
        },
        "original_invariant": {"type": "string", "minLength": 1},
        "upgraded_invariant": {"type": "string", "minLength": 1},
        "monotonicity_justification": {"type": "string", "minLength": 1}
      },
      "allOf": [
        {
          "if": {"properties": {"upgrade_applied": {"const": True}}},
          "then": {"required": ["upgrade_type", "original_invariant", "upgraded_invariant", "monotonicity_justification"]}
        },
        {
          "if": {"properties": {"upgrade_applied": {"const": False}}},
          "then": {
            "not": {
              "anyOf": [
                { "required": ["upgrade_type"] },
                { "required": ["original_invariant"] },
                { "required": ["upgraded_invariant"] },
                { "required": ["monotonicity_justification"] }
              ]
            }
          }
        }
      ]
    }
  }
}

UPGRADE_RANK = f"""You are a strict scientific benchmark evaluator for the subject area: {config.subject}. You are evaluating the structural validity of a mechanism.

Input:
A canonical mechanism JSON containing:

{{
  "mechanism_unit": "...",
  "requires": [...],
  "invariants": [...],
  "produces": [...],
  "failure_modes": [...],
  "minimal_example": "...",
  "upgrade_analysis": {{
      "upgrade_applied": boolean,
      ...
  }}
}}

Your task:
Determine whether this mechanism is structurally coherent, faithful to its original identity, and internally consistent. Classify it into one of the following levels:

L1 — Mechanism Structurally Altered
L2 — Non-Monotonic Strengthening or Internal Distortion
L3 — Hidden Assumption Extension
L4 — Structurally Valid but Underspecified
L5 — Structurally Sound and Faithful

-----------------------------------------
Evaluation Dimensions
-----------------------------------------

1. Preconditions Integrity

- Are all "requires" genuine operating preconditions?
- Are they necessary rather than descriptive?
- Are they mutually consistent?

If violated → L1

-----------------------------------------

2. Structural Identity Preservation

Check whether:

- Core causal structure remains unchanged.
- No new functional components are introduced.
- No causal dependencies are altered.
- produces remain consistent with invariants.

If structural identity changes → L1

-----------------------------------------

3. Invariant Consistency

Check:

- Are invariants structurally necessary?
- Do failure_modes correspond to violations of requires or invariants?
- Do invariants contradict produces?

If major logical inconsistency → L2

-----------------------------------------

4. Strengthening Validity (If upgrade_applied = true)

Verify:

- requires unchanged.
- produces unchanged.
- No new functional components introduced.
- No expansion of mechanism scope.
- Upgraded invariant is strictly stronger than original invariant.
- Strengthening is monotonic (tightening constraints, not redefining mechanism).

If structural alteration → L1  
If strengthening is non-monotonic or unjustified → L2

-----------------------------------------

5. Hidden Assumption Leakage

Check whether the mechanism:

- Introduces unstated environmental conditions.
- Relies on implicit domain assumptions not present in requires.
- Claims stability or generality without structural support.

If such extension exists → L3

-----------------------------------------

Decision Logic
-----------------------------------------

If structural alteration detected → L1
Else if non-monotonic strengthening detected → L2
Else if hidden assumption extension detected → L3
Else if coherent but underspecified → L4
Else → L5

-----------------------------------------

Output Format:

{{
  "level": "L1 | L2 | L3 | L4 | L5",
  "violations": ["..."],
  "explanations": "Concise structural explanation"
}}

Return only JSON. No additional commentary."""

UPGRADE_RANK_SCHEMA = {
    "type": "object",
    "required": ["level", 'violations', 'explanations'],
    'properties': {
        "level": {'type': 'string', 'enum': [f"L{i}" for i in range(1, 6)]},
        "violations": {"type": 'array', 'items': {"type": 'string', 'minLength': 1}},
        "explanations": {"type": 'string', 'minLength': 1}
    },
    "additionalProperties": False
}

PERTURB = """You are a senior research scientist in {subject}. You are generating scientific reasoning perturbations for a benchmark construction pipeline.

You are given a mechanism specification containing:

- mechanism_unit
- requires
- invariants
- produces
- failure_modes
- minimal_example

You MUST generate perturbations strictly following the LEVEL definition below.

------------------------------------------------------------
LEVEL DEFINITION

{requirements}
------------------------------------------------------------

CRITICAL RULES (MANDATORY):

1. You must generate exactly {number} perturbations.
2. Do NOT invent new requires, invariants, or failure_modes.
3. modified_* fields must be subsets of the original mechanism fields.
4. preserved_* fields must contain all remaining unmodified elements.
5. modified_* and preserved_* must NOT overlap.
6. The union of modified_* and preserved_* must exactly equal the original set.
7. Output STRICT JSON ONLY. No explanation text.

------------------------------------------------------------
GENERATION PROCEDURE (Follow in order for each perturbation)

Step 1. Decide which components are modified according to the LEVEL rule.
Step 2. Fill modified_* arrays.
Step 3. Fill preserved_* arrays so that coverage is complete and disjoint.
Step 4. Write structural_scenario consistent with modifications.
Step 5. Write tension_location explaining where reasoning difficulty arises.

------------------------------------------------------------
OUTPUT FORMAT
------------------------------------------------------------

```json
{{
  "perturbations": [
    {{
      "level": "L{level}",
      "perturbation_family": "...",
      "perturbation_operation": "...",
      "modified_requires": [...],
      "modified_invariants": [...],
      "modified_failure_modes": [...],
      "preserved_requires": [...],
      "preserved_invariants": [...],
      "preserved_failure_modes": [...],
      "structural_scenario": "...",
      "tension_location": "..."
    }}
  ]
}}
```
"""

PERTURB_DETAILS = [
    """**LEVEL: L1 Instance Reparameterization**

**Modification rule:**

* modified_requires MUST be [].
* modified_invariants MUST be [].
* modified_failure_modes MUST be [].
* invariant_status MUST be "preserved".

**Meaning of modification:**
Construct an alternative scenario that preserves all requires, invariants, and failure_modes.
Entities, tokens, or example domains can be changed, and new concrete examples can be instantiated.
The scenario must still claim requires_satisfied = true and failure_not_triggered = true.

**You MUST NOT:**

* Modify any structural logic (requires, produces, invariants, failure_modes).
* Trigger any failure_mode.""",
    """**LEVEL: L2 Requires Weakening**

**Modification rule:**

* Exactly ONE element from requires must appear in modified_requires.
* modified_invariants MUST be [].
* modified_failure_modes MUST be [].
* invariant_status MUST be "preserved".

**Meaning of modification:**
The selected requires condition is weakened or removed, but the scenario must still claim requires_satisfied = true under the weakened interpretation.

**You MUST NOT:**

* Modify invariants.
* Modify failure_modes.
* Trigger any failure condition.""",
    """**LEVEL: L3 Failure Boundary Deformation**

**Modification rule:**

* modified_failure_modes MUST contain exactly one boundary-altered failure_mode.
* modified_requires MUST be [].
* modified_invariants MUST be [].
* invariant_status MUST be "preserved".

**Meaning of modification:**
The scenario lies near the failure boundary of the selected failure_mode but does not fully trigger it.
All requires and invariants remain satisfied.
You can perform threshold perturbation, temporal delay, or partial activation.

**You MUST NOT:**

* Violate requires.
* Violate invariants.
* Fully trigger the failure_mode.""",
    """**LEVEL: L4 Invariant Violation**

**Modification rule:**

* At least one invariant must appear in modified_invariants.
* modified_requires MUST be [].
* modified_failure_modes MUST be [].
* invariant_status MUST be "partially_violated".

**Meaning of modification:**
Construct a scenario where at least one invariant is violated, while all requires are satisfied.
The scenario must not directly trigger any existing failure_mode and must remain superficially applicable.

**You MUST NOT:**

* Modify requires.
* Trigger any failure_mode.""",
    """**LEVEL: L5 Invariant Substitution**

**Modification rule:**

* Exactly one invariant must appear in modified_invariants (the substituted invariant).
* modified_requires MUST be [].
* modified_failure_modes MUST be [].
* invariant_status MUST be "substituted".

**Meaning of modification:**
Replace the selected invariant with a structurally different invariant.
All requires must remain satisfied, and the mechanism must remain internally coherent.
The new invariant must not be logically equivalent to the original.

**You MUST NOT:**

* Modify requires.
* Trigger any failure_mode."""
]

PERTURB_NUMBERS = [2, 2, 2, 3, 2]


def PERTURB_SCHEMA(level: int):
    modified_requires = {"type": "array", "items": {"type": "string", "minLength": 1}, "minItems": 1} if level == 1 else {"const": []}
    modified_invariants = {"type": "array", "items": {"type": "string", "minLength": 1}, "minItems": 1} if level > 2 else {"const": []}
    modified_failure_modes = {"type": "array", "items": FAILURE_MODE_SCHEMA, "minItems": 1} if level == 2 else {"const": []}
    return {
        "type": "object",
        "required": ["perturbations"],
        "properties": {
            "perturbations": {
                "type": "array",
                "minItems": PERTURB_NUMBERS[level],
                "items": {
                    "type": "object",
                    "required": ["level", "perturbation_family", "perturbation_operation", "modified_requires",
                                "modified_invariants", "modified_failure_modes", "preserved_requires",
                                "preserved_invariants", "preserved_failure_modes", "structural_scenario",
                                "tension_location"],
                    "properties": {
                        "level": {"const": f"L{level + 1}"}, 
                        "perturbation_family": {"type": "string", "minLength": 1}, 
                        "perturbation_operation": {"type": "string", "minLength": 1}, 
                        "modified_requires": modified_requires,
                        "modified_invariants": modified_invariants, 
                        "modified_failure_modes": modified_failure_modes, 
                        "preserved_requires": {"type": "array", "items": {"type": "string", "minLength": 1}},
                        "preserved_invariants": {"type": "array", "items": {"type": "string", "minLength": 1}}, 
                        "preserved_failure_modes": {"type": "array", "items": FAILURE_MODE_SCHEMA}, 
                        "structural_scenario": {"type": "string", "minLength": 1},
                        "tension_location": {"type": "string", "minLength": 1}
                    },
                    "additionalProperties": False
                }
            }
        },
        "additionalProperties": False
    }


GENERATE = f"""You are a senior research scientist in {config.subject}.

Your task is to generate THREE scientifically realistic multiple-choice questions based strictly on the provided paper.

Each question must contain EXACTLY FIVE answer options (A–E). Exactly ONE option must be correct.

### IMPORTANT DESIGN SHIFT:

- The goal is NOT to create a pure logic puzzle.
- The goal is to simulate realistic scientific reasoning under constrained evidence.

### REQUIREMENTS

1. Scientific realism
- The scenario must resemble an actual research setting.
- Include concrete experimental or analytical conditions.
- Include at least one observation or result that could plausibly support more than one interpretation.
- Do NOT introduce assumptions that contradict real-world scientific constraints.

2. Reasoning structure
- The correct answer must require synthesizing at least TWO stated conditions.
- The incorrect options must each fail because they:
  (a) over-generalize,
  (b) ignore a stated constraint,
  (c) assume an unsupported mechanism,
  or (d) misinterpret the direction of causality.

3. Difficulty control
- Avoid trivial elimination (e.g., arithmetic-only reasoning).
- Avoid questions answerable by single-sentence scanning.
- Do NOT rely on unstated domain facts.
- Do NOT test recall of literature.

4. Options
- All options must be plausible within the field.
- No option may be obviously false without referencing the scenario.
- Avoid generic statements that would apply to most systems.

5. Explanation
For each question:
- Explain why the correct option best accounts for ALL stated conditions.
- Explain precisely which condition each incorrect option fails to satisfy.

### OUTPUT FORMAT

Output ONLY in the following JSON format:
```json
{{
  "questions": [
    {{
      "question": "...",
      "options": {{
        "A": "...",
        "B": "...",
        "C": "...",
        "D": "...",
        "E": "..."
      }},
      "answer": "A" | "B" | "C" | "D" | "E",
      "explanations": "..."
    }}
  ]
}}
```
"""

QUESTION_SCHEMA = {
  "type": "object",
  "required": ["question", "options", "answer", "explanations"],
  "properties": {
    "question": {"type": "string", "minLength": 1},
    "options": {
      "type": "object",
      "required": OPTIONS,
      "properties": {k: {"type": "string", "minLength": 1} for k in OPTIONS}
    },
    "answer": {"type": "string", "enum": OPTIONS},
    "explanations": {"type": "string"}
  },
  "additionalProperties": False
}

GENERATE_SCHEMA = {
  "type": "object",
  "required": ['questions'],
  "properties": {
    "questions": {
      "type": "array",
      "items": QUESTION_SCHEMA
    }
  },
  "additionalProperties": False
}

FILTER = f"""You are a strict scientific benchmark filter for the subject area: {config.subject}. Your task is to decide whether the given multiple-choice question should be eliminated because answering it would require access to paper-specific details rather than scientific reasoning, or because it lacks strong relevance to the subject area.

A question MUST be eliminated if correct answering requires:
- Referring to a specific figure, table, equation, or section from a paper
- Recalling exact numerical values, sample labels, dataset names, or configuration details not stated in the question
- Remembering experimental or analytical conditions not explicitly stated in the question
- Concluding "insufficient information is given" as the main reasoning step
- Applying only generic reasoning that would equally apply to most scientific disciplines, without substantive connection to {config.subject}

A question MUST be retained if it can be answered through:
- Logical consequences of explicitly stated assumptions
- Conceptual reasoning about mechanisms, principles, or theoretical structures central to {config.subject}
- Comparing competing interpretations within the conceptual framework of {config.subject}
- High-level domain knowledge specific to {config.subject}, without requiring recall of paper-specific details

IMPORTANT:
The question must demonstrate clear and substantive dependence on core concepts, methods, or theoretical structures of {config.subject}. If it could be answered equally well without subject-specific expertise, it must be eliminated.

Output ONLY in JSON format:

```json
{{
  "eliminate": true | false,
  "reason": "brief explanation"
}}
```
"""

REVISE = """You are an expert scientific question designer. You are given a well-formed multiple-choice question with 5 options and a single correct answer. 

Your task is to IMPROVE the question while preserving:
- The core research scenario
- The single correct answer
- EXACTLY FIVE answer options

You must NOT increase the number of options.

### OBJECTIVES

1. Increase reasoning depth WITHOUT introducing new scientific assumptions.
- You may clarify experimental conditions.
- You may make implicit constraints explicit.
- You may refine wording to remove trivial eliminations.

2. Eliminate superficial logic shortcuts.
- Remove wording that allows answer selection by pattern matching.
- Ensure the correct option requires integrating multiple conditions.

3. Scientific coherence check.
- Verify the scenario does not contradict known scientific principles.
- Do NOT introduce impossible or mutually exclusive conditions.

4. Option tightening.
For each incorrect option:
- Ensure it fails for exactly ONE identifiable reason.
- Ensure that reason depends on a stated condition.

5. Self-audit before finalizing:
- Would a domain expert need to reason through the evidence?
- Could the answer be guessed without analyzing the scenario?
- Are all options anchored to the specific context?

### OUTPUT FORMAT

Output JSON only:
```json
{
  "question": "...",
  "options": {
    "A": "...",
    "B": "...",
    "C": "...",
    "D": "...",
    "E": "..."
  },
  "answer": "...",
  "explanations": "..."
}
```
"""

REVISE_SCHEMA = {
  "type": "object",
  "required": ["question", "options", "answer", "explanations"],
  "properties": {
    "question": {"type": "string", "minLength": 1},
    "options": {
      "type": "object",
      "required": EXPAND_OPTIONS,
      "properties": {k: {"type": "string", "minLength": 1} for k in EXPAND_OPTIONS},
      "additionalProperties": False
    },
    "answer": {"type": "string", "enum": EXPAND_OPTIONS},
    "explanations": {"type": "string"}
  },
  "additionalProperties": False
}

SELF_CONTRADICT = """You are a strict scientific benchmark filter. You are given a scientific multiple-choice question stem. Your task is to judge whether the question stem itself is internally self-contradictory.

Definition:
A stem is self-contradictory if it simultaneously assumes statements that cannot all be true under any reasonable scientific or theoretical interpretation.

Instructions:
- Do NOT evaluate answer options.
- Do NOT judge realism or probability.
- Only check whether the assumptions in the stem can logically and coherently coexist.

Output format:
```json
{
  "self_contradictory": true | false,
  "reason": "brief explanation"
}
```
"""

REDUNDANT = """You are a strict scientific benchmark filter. You are given a scientific multiple-choice question. Your task is to judge whether the question stem contains information that:
- Is not required to determine the correct answer, AND
- Does not meaningfully function as a distractor for any option.

Instructions:
- Do NOT assume perfect exam design.
- Only flag information that is clearly irrelevant to all options.
- If unsure, answer "no".

Output format:
```json
{
  "contains_redundant_information": true | false,
  "reason": "brief explanation"
}
```
"""

IMPLAUSIBLE = """You are a strict scientific benchmark filter. You are given a scientific question. Your task is to judge whether the combination of assumptions described in the question is considered:
- Extremely atypical, or
- Violating well-established physical or scientific principles.

Instructions:
- Judge the combination of assumptions, not individual statements.
- Do NOT require absolute impossibility; extreme implausibility is sufficient.
- Ignore purely hypothetical or philosophical framing.

Output format:
```json
{
  "physically_implausible": true | false,
  "reason": "brief explanation"
}
```
"""

CANONICAL = f"""You are an expert on {config.subject}. You are given an answer option from a scientific multiple-choice question. Rewrite the option into a canonical form that:
- States only the core claim being asserted
- Removes rhetorical phrasing, examples, and hedging
- Does NOT add assumptions from the question stem

Output format:
```json
{{
  "canonical_statement": "one concise declarative sentence"
}}
```
"""

OPTION_CHECK = """You are a strict scientific benchmark filter. You are reviewing a multiple-choice question for quality control. Your task is to identify structural issues that can be judged WITHOUT solving the problem.

Given the question and options below, analyze them under the following rules:

Definitions:
- "Trivially true without the question" means the option is obviously correct based on general knowledge alone.
- "Trivially false without the question" means the option is obviously incorrect or nonsensical based on general knowledge alone.
- "Does not depend on the question" means the option makes a standalone claim so that a knowledgeable reader can decide whether the option is true or false even if the question context is removed.
- "Semantically redundant options" are options that express essentially the same idea or mechanism, even if worded differently.

Instructions:
- Do NOT judge which option is correct given the question.
- Do NOT use information outside the text unless it is general domain knowledge.
- Be conservative: only label cases that are clear and unambiguous.

Output a JSON object with the following fields:
```json
{
  "trivially_true_without_question": <list of option letters>,
  "trivially_false_without_question": <list of option letters>,
  "does_not_depend_on_question": <list of option letters>,
  "redundant_options": <list of lists of option letters>
}
```
"""

OPTION_SCHEMA = {
    "type": "object", 
    "required": [
        "trivially_true_without_question",
        "trivially_false_without_question",
        "does_not_depend_on_question",
        "redundant_options"
    ],
    "properties": {
        "trivially_true_without_question": {
            "type": "array",
            "items": {
                "type": "string", 
                "enum": EXPAND_OPTIONS
            }
        },
        "trivially_false_without_question": {
            "type": "array",
            "items": {
                "type": "string", 
                "enum": EXPAND_OPTIONS
            }
        },
        "does_not_depend_on_question": {
            "type": "array",
            "items": {
                "type": "string", 
                "enum": EXPAND_OPTIONS
            }
        },
        "redundant_options": {
            "type": "array",
            "items": {
                "type": "array",
                "minItems": 2,
                "items": {
                    "type": "string",
                    "enum": EXPAND_OPTIONS
                }
            }
        }    
    }
}

TEST = f"""You are an expert on {config.subject}. You are asked to answer the following multiple-choice question.

If you determine that:
- the assumptions are internally contradictory,
- the question cannot be meaningfully adjudicated given its stated assumptions,
- or the question is ill-posed as a scientific query,

you MUST select option {NOT_ANSWERABLE}: "None of the above. / This question is unanswerable".

Otherwise, select the single best answer.

Do NOT explain your reasoning. Output only the selected option letter, in the following JSON format:

```json
{{ "selected_answer": "A" | "B" | "C" | "D" | "E" }}
```
"""

TEST_SCHEMA = {
  "type": "object",
  "required": ["selected_answer"],
  "properties": {"selected_answer": {"type": "string", "enum": EXPAND_OPTIONS + [NOT_ANSWERABLE]}},
  "additionalProperties": False
}
