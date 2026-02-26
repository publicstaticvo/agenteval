from config import Config
config = Config.from_yaml("config.yaml")
OPTIONS = ['A', 'B', 'C', 'D']
EXPAND_OPTIONS = ['A', 'B', 'C', 'D']
NOT_ANSWERABLE = "E"
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

UPGRADE_RANK = f"""You are a strict scientific mechanism structural evaluator for the subject area: {config.subject}. You are evaluating the structural validity of a mechanism.

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
Your task is to evaluate mechanism M0 along four structural dimensions.

------------------------------------------------------------
EVALUATION DIMENSIONS
------------------------------------------------------------

1. Structural Explicitness
   - Are requires and invariants clearly separable?
   - Are they explicitly stated rather than implied?
   - Can they be individually referenced?

2. Modular Dependency
   - Can at least one require be modified without collapsing all invariants?
   - Is the mechanism dependency graph non-trivial but not fully entangled?

3. Invariant Rigidity
   - Is there at least one invariant that constrains behavior?
   - Would modifying that invariant meaningfully change outcomes?

4. Context Sensitivity
   - Does minimal_example depend on boundary conditions or contextual factors?
   - Can scenario changes expose hidden tension?

------------------------------------------------------------
OUTPUT FORMAT
------------------------------------------------------------

```json
{{
  "structural_explicitness": true | false,
  "modular_dependency": true | false,
  "invariant_rigidity": true | false,
  "context_sensitivity": true | false,
  "explanation": "Detailed reasoning."
}}
```"""

UPGRADE_RANK_SCHEMA = {
    "type": "object",
    "required": ["structural_explicitness", "modular_dependency", "invariant_rigidity", "context_sensitivity", "explanation"],
    'properties': {
        "structural_explicitness": {"type": "boolean"}, 
        "modular_dependency": {"type": "boolean"}, 
        "invariant_rigidity": {"type": "boolean"}, 
        "context_sensitivity": {"type": "boolean"},
        "explanation": {"type": 'string', 'minLength': 1}
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
------------------------------------------------------------

{requirements}

------------------------------------------------------------
GENERATION PROCEDURE (Follow in order for each perturbation)
------------------------------------------------------------

Step 1. Decide which components are modified according to the LEVEL rule.
Step 2. Fill modified_* arrays.
Step 3. Fill preserved_* arrays so that coverage is complete and disjoint.
Step 4. Derive new_produces as the logical consequence of modified_requires.new + preserved_requires + modified_invariants.new + preserved_invariants.
Step 5. Derive new_failure_modes strictly as violations of modified_requires.new or modified_invariants.new. Failure modes must be consistent with the new mechanism structure. Do NOT reuse old failure_modes verbatim unless they still logically apply.
Step 6. Write new minimal_example consistent with modifications.
Step 7. Write tension_location explaining where reasoning difficulty arises.

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
      "modified_requires": [
        {{
          "origin": "...",
          "new": "..."
        }},
        ...
      ],
      "modified_invariants": [
        {{
          "origin": "...",
          "new": "..."
        }},
        ...
      ],
      "preserved_requires": [...],
      "preserved_invariants": [...],
      "new_produces": [...],
      "new_failure_modes": [
        {{
          "violated_component": "requires" | "invariants",
          "violation_description": "...",
          "original_break_condition": "..."
        }},
        ...
      ],
      "minimal_example": "...",
      "tension_location": "..."
    }}
  ]
}}
```
------------------------------------------------------------
CRITICAL RULES (MANDATORY)
------------------------------------------------------------

1. You must generate exactly {number} comprehensive, non-trivial perturbations.
2. Do NOT invent new requires, invariants, or failure_modes.
3. modified_*.origin fields must be subsets of the original mechanism fields. Fill modified_*.new fields as your rewritten content.
4. preserved_* fields must contain all remaining unmodified elements.
5. modified_*.origin and preserved_* must NOT overlap.
6. The union of modified_*.origin and preserved_* must exactly equal the original set.
7. Output STRICT JSON ONLY. No explanation text.

The new minimal_example must:

* Explicitly instantiate all requires.
* Respect all invariants.
* Not accidentally trigger an obvious failure mode (unless the level definition requires boundary stress).
"""

PERTURB_REQUIREMENTS = [
"""LEVEL L1: Boundary Stress (Invariant-Preserving Example Shift)

You must NOT modify:
- Any requires
- Any invariants
- Any failure_modes
- The mechanism_unit
- The produces

You are allowed to modify:
- minimal_example ONLY

How to modify:

1. Keep all requires EXACTLY unchanged.
2. Keep all invariants EXACTLY unchanged.
3. Keep failure_modes and produces EXACTLY unchanged.
4. Construct a new minimal_example that:
   - Explicitly instantiates all original requires.
   - Fully respects all invariants.
   - Moves the scenario closer to a known failure mode, but does NOT actually trigger it. Also, do NOT violate any requires or invariants.
   - Increases reasoning tension by creating ambiguity about whether a failure might occur.

The perturbation must:
- Stress-test the mechanism.
- Introduce edge-case conditions.
- Remain logically valid under the original mechanism.

You must NOT:
- Weaken or strengthen any invariant.
- Implicitly introduce new assumptions.
- Accidentally trigger any failure mode.
- Modify produces or reinterpret mechanism_unit.""",
"""LEVEL L2: Requires Modification (Invariant-Preserving Assumption Shift)

You must NOT modify:
- Any invariants
- Any failure_modes
- The mechanism_unit
- The produces

You are allowed to modify:
- One or more requires
- minimal_example

How to modify:

1. Modify selected requires while keeping invariants EXACTLY unchanged.
2. The modified requires must still logically support all original invariants.
   (If invariants no longer logically follow, the perturbation becomes invalid.)
3. Do NOT introduce new invariants.
4. Do NOT weaken or strengthen invariants.
5. Construct a new minimal_example that:
   - Satisfies the modified requires.
   - Fully respects all invariants.
   - Does NOT trigger any failure mode.

The perturbation must:
- Change the assumption structure of the mechanism.
- Preserve the structural constraint represented by invariants.
- Create reasoning difficulty due to altered preconditions.

You must NOT:
- Modify invariants in any form.
- Introduce hidden background assumptions.
- Create logical inconsistency between requires and invariants.""",
"""LEVEL L3: Invariant Modification (Structural Mechanism Change)

You must modify:
- At least one invariant

You may also modify:
- One or more requires (only if logically necessary)
- minimal_example

How to modify:

1. Change at least one invariant by:
   - Weakening it,
   - Strengthening it,
   - Inverting it,
   - Replacing it with a structurally different constraint.
2. If necessary, adjust requires so that the new invariant is logically coherent.
3. Do NOT preserve the original invariant if it conflicts with the new one.
4. Derive new_produces and new_failure_modes.
5. Construct a new minimal_example that:
   - Satisfies the modified requires.
   - Fully respects the modified invariants.
   - Does NOT trigger explicit failure modes unless logically required.

The perturbation must:
- Alter the structural logic of the mechanism.
- Create multi-step reasoning tension.
- Force evaluation of invariant-level consistency.

You must NOT:
- Keep invariants unchanged.
- Introduce arbitrary new invariants unrelated to the mechanism.
- Modify produces.
- Collapse the perturbation into a mere requires adjustment (which would be L2)."""
]

PERTURB_NUMBERS = [3, 3, 3]


def PERTURB_SCHEMA(level: int):
    replace = {"type": "object", "required": ['origin', 'new'], "properties": {"origin": {"type": "string", "minLength": 1}, "new": {"type": "string", "minLength": 1}}}
    modified_invariants = {"type": "array", "items": replace, "minItems": 1} if level == 2 else {"const": []}
    if level == 0:
        modified_requires = {"const": []}
        required = ["level", "perturbation_family", "perturbation_operation", "new_failure_modes", 
                    "preserved_requires", "preserved_invariants", "minimal_example", "new_produces", 
                    "tension_location"]
    elif level == 1:
        modified_requires = {"type": "array", "items": replace, "minItems": 1}
        required = ["level", "perturbation_family", "perturbation_operation", "new_failure_modes", 
                    "preserved_requires", "preserved_invariants", "minimal_example", "new_produces", 
                    "tension_location", "modified_requires"]
    else:
        modified_requires = {"type": "array", "items": replace}
        required = ["level", "perturbation_family", "perturbation_operation", "new_failure_modes", 
                    "preserved_requires", "preserved_invariants", "minimal_example", "new_produces", 
                    "tension_location", "modified_invariants"]
    return {
        "type": "object",
        "required": ["perturbations"],
        "properties": {
            "perturbations": {
                "type": "array",
                "minItems": PERTURB_NUMBERS[level],
                "items": {
                    "type": "object",
                    "required": required,
                    "properties": {
                        "level": {"const": f"L{level + 1}"}, 
                        "perturbation_family": {"type": "string", "minLength": 1}, 
                        "perturbation_operation": {"type": "string", "minLength": 1}, 
                        "modified_requires": modified_requires,
                        "modified_invariants": modified_invariants,
                        "preserved_requires": {"type": "array", "items": {"type": "string", "minLength": 1}},
                        "preserved_invariants": {"type": "array", "items": {"type": "string", "minLength": 1}}, 
                        "new_produces": {"type": "array", "items": {"type": "string", "minLength": 1}}, 
                        "new_failure_modes": {"type": "array", "items": FAILURE_MODE_SCHEMA}, 
                        "minimal_example": {"type": "string", "minLength": 1},
                        "tension_location": {"type": "string", "minLength": 1}
                    }
                }
            }
        },
        "additionalProperties": False
    }


PERTURB_VALIDITY = f"""You are a formal scientific mechanism validator for the subject area: {config.subject}. You are given:

- Original mechanism M0
- Perturbed mechanism M'

Your task is to evaluate the INTERNAL VALIDITY of M'.

------------------------------------------------------------
CHECK CATEGORY — Logical Integrity
------------------------------------------------------------

Verify that M':

1. Is non-trivial.
   (Not a restatement of obvious consequences.)
2. Is internally consistent.
   (No contradiction between requires, invariants, produces.)
3. Is plausible in a realistic scientific setting.
4. Has scientific significance.
   (Would reasoning about it matter in real research?)
5. new_produces are logically derivable from:
   - mechanism_unit
   - modified requires
   - modified invariants
6. new_failure_modes are correctly derived from violated components.

------------------------------------------------------------
OUTPUT FORMAT (STRICT JSON)
------------------------------------------------------------

```json
{{
  "is_non_trival": true | false,
  "is_internally_consistent": true | false,
  "is_plausible": true | false,
  "has_scientific_significance": true | false,
  "is_logically_derivable": true | false,
  "is_correctly_derived": true | false,
  "explanation": "..."
}}
```"""

PERTURB_CHECK_USER = """
------------------------------------------------------------
Original mechanism (M0)
------------------------------------------------------------

{origin}

------------------------------------------------------------
Perturbed mechanism (M')
------------------------------------------------------------

{unit}"""

PERTURB_VALIDITY_SCHEMA = {
    "type": "object",
    "required": ["is_non_trival", "is_internally_consistent", "is_plausible", "has_scientific_significance", "is_logically_derivable", "is_correctly_derived", "explanation"],
    'properties': {
      "is_non_trival": {"type": "boolean"},
      "is_internally_consistent": {"type": "boolean"},
      "is_plausible": {"type": "boolean"},
      "has_scientific_significance": {"type": "boolean"},
      "is_logically_derivable": {"type": "boolean"},
      "is_correctly_derived": {"type": "boolean"},
      "explanation": {"type": "string", "minLength": 1}
    },
    "additionalProperties": False
}

PERTURB_DEGENERATION = f"""You are a formal scientific mechanism validator for the subject area: {config.subject}. You are given:

- Original mechanism M0
- Perturbed mechanism M'

Your task is to evaluate whether M' is a genuine perturbation.

------------------------------------------------------------
CHECK CATEGORY — Perturbation Difference
------------------------------------------------------------

1. M' must NOT be logically equivalent to M0.
2. The perturbation must generate a new reasoning requirement.
3. The perturbation must change the inferential path or constraint interaction.
4. M' must represent a genuinely different mechanism state.

------------------------------------------------------------
OUTPUT FORMAT (STRICT JSON)
------------------------------------------------------------

```json
{{
  "non_equivalence": true | false,
  "generates_new_reasoning_pattern": true | false,
  "explanation": "..."
}}
```"""

PERTURB_DEGENERATION_SCHEMA = {
    "type": "object",
    "required": ["non_equivalence", "generates_new_reasoning_pattern", "explanation"],
    'properties': {
      "non_equivalence": {"type": "boolean"},
      "generates_new_reasoning_pattern": {"type": "boolean"},
      "explanation": {"type": "string", "minLength": 1}
    },
    "additionalProperties": False
}

PERTURB_SEMANTIC = """You are a formal scientific mechanism validator for the subject area: {subject}.

You are given:

1. Original mechanism M0
2. Perturbed mechanism M'
3. Target Level: {description}

------------------------------------------------------------
OUTPUT FORMAT
------------------------------------------------------------

Output JSON only:

```json
{{
  "level_semantic_validity": "accept" | "reject",
  "explanation": "..."
}}
```"""

PERTURB_SEMANTIC_CHECK = [
"""L1 Boundary Stress (Invariant-Preserving Example Shift)

------------------------------------------------------------
SEMANTIC REQUIREMENTS
------------------------------------------------------------

1. The new minimal_example must move closer to a known failure boundary.
2. It must reduce safety margin without triggering failure.
3. It must increase ambiguity about failure risk.
4. It must increase reasoning tension compared to M0.

Reject if:
- It is merely a cosmetic example change.
- It does not meaningfully approach a boundary.
- It makes reasoning easier instead of harder.""",
"""L2 Requires Modification (Invariant-Preserving Assumption Shift)

------------------------------------------------------------
SEMANTIC REQUIREMENTS
------------------------------------------------------------

1. Requires must be meaningfully modified.
2. The new requires must alter the inferential starting point.
3. Invariants must remain structurally intact.
4. The new requires must still logically support all invariants.
5. The reasoning path must differ from M0.

Reject if:
- The modification is superficial or equivalent.
- The new requires are redundant.
- The invariants become unsupported.
- The perturbation collapses into L1.""",
"""L3 Invariant Modification (Structural Mechanism Change)

------------------------------------------------------------
SEMANTIC REQUIREMENTS
------------------------------------------------------------

1. At least one invariant must be structurally changed.
2. The new invariant must alter the constraint structure.
3. The modification must expand, shrink, or reshape the admissible mechanism space.
4. The reasoning process must change at the structural level.

Reject if:
- The invariant change is merely a rewording.
- The inferential structure remains identical.
- The perturbation is reducible to a requires-only change (L2).""",
]

PERTURB_CRITIC = """You are an adversarial scientific perturbation critic for the subject area: {subject}. Your task is to determine whether the perturbed mechanism M' constitutes a VALID and USEFUL perturbation of M0 under the specified Level constraint.

You are NOT checking formatting or checking schema compliance. You are evaluating reasoning transformation.

You are given:

1. Original mechanism M0
2. Perturbed mechanism M'
3. Target Level: {level_description}

------------------------------------------------------------
EVALUATION OBJECTIVES
------------------------------------------------------------

You must evaluate the following dimensions:

(1) Reasoning Transformation

Does M' require a different reasoning pathway than M0?

Assess whether the original solution strategy can:
- be reused exactly
- be reused with minor modification
- fails completely

------------------------------------------------------------

(2) Level-Consistent Disruption

Does the magnitude and type of disruption match the Level definition?

The required type of disruption of the level {level} is {mini_description}.

Reject if disruption is:
- weaker than required
- stronger than allowed
- type-mismatched

------------------------------------------------------------

(3) Problem Generativity

Would M' naturally generate a new scientific question?

Specifically:
- Does it introduce a new uncertainty?
- Does it force new inference steps?
- Does it create new trade-offs or failure analysis?

------------------------------------------------------------

(4) Degeneracy Detection

Detect whether M' is:

- Trivial restatement
- Linguistic paraphrase
- Boundary shift with no reasoning effect
- Equivalent invariant disguised as substitution
- Internally incoherent

------------------------------------------------------------

OUTPUT FORMAT
------------------------------------------------------------

Output JSON only:

```json
{{
  "reasoning_shift": "none" | "minor" | "structural",
  "solution_reuse_status": "exact_reuse" | "minor_modification" | "new_framework_required",
  "level_disruption_match": "valid" | "underpowered" | "overpowered" | "wrong_type",
  "generates_new_problem": true | false,
  "degeneracy_detected": true | false,
  "scientific_tension_introduced": "none" | "moderate" | "strong",
  "final_verdict": "accept" | "reject",
  "analysis_summary": "Concise explanation."
}}"""

PERTURB_CRITIC_DESCRIPTION = [
"""L1 Boundary Stress (Invariant-Preserving Example Shift)
Failure boundary or operational regime changed. Requires and invariants preserved. Increased reasoning depth required.""",
"""L2 Requires Modification (Invariant-Preserving Assumption Shift)
At least one requires condition modified. Invariants preserved. Reasoning framework adjusted but not destroyed.""",
"""L3 Invariant Modification (Structural Mechanism Change)
Core invariant replaced by a different structural principle. Mechanism ontology shifts. New conceptual framing required."""
]

PERTURB_CRITIC_MINI_DESCRIPTION = [
    "boundary deformation",
    "requires-space shift", 
    "invariant replacement"
]

PERTURB_CRITIC_SCHEMA = {
    "type": "object",
    "required": ["reasoning_shift", "solution_reuse_status", "level_disruption_match",
                 "generates_new_problem", "degeneracy_detected", "scientific_tension_introduced",
                 "final_verdict", "analysis_summary"],
    "properties": {
        "reasoning_shift": {"type": "string", "enum": ["none", "minor", "structural"]}, 
        "solution_reuse_status": {"type": "string", "enum": ["exact_reuse", "minor_modification", "new_framework_required"]}, 
        "level_disruption_match": {"type": "string", "enum": ["valid", "underpowered", "overpowered", "wrong_type"]},
        "generates_new_problem": {"type": "boolean"}, 
        "degeneracy_detected": {"type": "boolean"}, 
        "scientific_tension_introduced": {"type": "string", "enum": ["none", "moderate", "strong"]},
        "final_verdict": {"type": "string", "enum": ["accept", "reject"]}, 
        "analysis_summary": {"type": "string"}
    },
    "additionalProperties": False
}

GRAPH = """You are a structural reasoning graph constructor. Your task is to construct FOUR structurally symmetric reasoning graphs derived from the given scientific mechanism.

You are NOT generating prose explanations. You are NOT generating answer options. You are NOT writing a question paragraph. You are generating formal reasoning structures only.

--------------------------------------------
OUTPUT FORMAT (STRICT JSON)

{
  "mechanism_core": {
    "requires": [...],
    "invariants": [...],
    "failure_modes": [...]
  },
  "tension_node": {
    "structural_conflict": "...",
    "conflicting_components": [...]
  },
  "reasoning_graphs": [
    {
      "id": "A",
      "assumption_profile": {
        "scaling_assumption": "...",
        "boundary_assumption": "...",
        "invariant_handling": {
          "for_each_invariant": {
            "invariant_1": "preserved / reinterpreted / relaxed",
            "invariant_2": "...",
            ...
          }
        },
        "failure_mode_handling": {
          "for_each_failure_mode": {
            "failure_1": "triggered / suppressed / delayed",
            ...
          }
        }
      },
      "logical_progression": [
        "formal step 1",
        "formal step 2",
        "formal step 3"
      ],
      "predicted_outcome": "...",
      "is_correct": true/false
    },
    ...
  ]
}

--------------------------------------------
STRICT STRUCTURAL RULES

1. All four graphs must:
   - Handle every invariant explicitly.
   - Handle every failure_mode explicitly.
   - Use the same tension_node.
   - Have the same number of logical steps.

2. The only allowed difference between graphs:
   - Different invariant interpretation.
   - Different failure_mode activation logic.
   - Different scaling assumption.

3. Exactly ONE graph must be globally consistent. Others must fail due to structural inconsistency.

4. No natural language persuasion.
   No rhetorical strengthening.
   No extreme terms (strictly, necessarily, entirely).

5. If symmetry cannot be achieved, regenerate internally.
"""

GRAPH_SCHEMA = {
  "type": "object",
  "additionalProperties": False,
  "required": ["mechanism_core", "tension_node", "reasoning_graphs"],
  "properties": {
    "mechanism_core": {
        "type": "object",
        "additionalProperties": False,
        "required": ["requires", "invariants", "failure_modes"],
        "properties": {
            "requires": {"type": "array", "items": {"type": "string", "minLength": 1}},
            "invariants": {"type": "array", "items": {"type": "string", "minLength": 1}},
            "failure_modes": {"type": "array", "items": {"type": "string", "minLength": 1}}
        }
    },
    "tension_node": {
        "type": "object",
        "additionalProperties": False,
        "required": ["structural_conflict", "conflicting_components"],
        "properties": {
            "structural_conflict": {"type": "string", "minLength": 1},
            "conflicting_components": {"type": "array", "items": {"type": "string", "minLength": 1}}
        }
    },
    "reasoning_paths": {
      "type": "array",
      "minItems": 4,
      "maxItems": 4,
      "prefixItems": [
        {
          "type": "object",
          "additionalProperties": False,
          "required": ["id", "assumption_profile", "logical_progression", "predicted_outcome", "is_correct"],
          "properties": {
            "id": {"const": x},
            "logical_progression": {"type": "array", "items": {"type": "string", "minLength": 1}},
            "assumption_profile": {
              "type": "object",
              "additionalProperties": False,
              "required": ["scaling_assumption", "boundary_assumption", "invariant_handling", "failure_mode_handling"],
              "properties": {
                "scaling_assumption": {"type": "string", "minLength": 1},
                "boundary_assumption": {"type": "string", "minLength": 1},
                "invariant_handling": {
                    "type": "object",
                    
                },
                "failure_mode_handling": {"type": "array", "items": {"type": "string", "minLength": 1}}
              }
            },
            "predicted_outcome": {"type": "string", "minLength": 1},
            "is_correct": {"type": "boolean"}
          }
        }
        for x in OPTIONS
      ],
      "items": False
    }
  }
}

GENERATE = """You are a formal scientific question constructor. You are given:

- A structural reasoning graph with four symmetric paths.

Your task:
Transform the structural graph into a multiple-choice question.

--------------------------------------------
OUTPUT FORMAT (STRICT JSON)

{
  "mechanism_summary": "...",
  "question": "...",
  "options": [
    {"id": "A", "statement": "..."},
    {"id": "B", "statement": "..."},
    {"id": "C", "statement": "..."},
    {"id": "D", "statement": "..."}
  ],
  "correct_option": "A/B/C/D"
}

--------------------------------------------
MANDATORY CONSTRAINTS

1. The question must define all entities explicitly.
2. The phrase “the mechanism” is forbidden.
3. No undefined abbreviations.
4. Each option must correspond exactly to one reasoning_graph predicted_outcome.
5. You may NOT introduce new causal links.
6. Options must not differ in wording strength.
7. No option may contain absolute language.
8. The question must be solvable only by structural reasoning.

If mapping introduces new structure, regenerate internally.
"""

ERROR_PATTERN_SET = [
  "Overgeneralization",
  "Hidden Assumption Injection",
  "Invariant Confusion",
  "Requires-Produce Conflation",
  "Failure Mode Neglect",
  "Causal Direction Reversal",
  "Boundary Condition Misapplication",
  "Overfitting to Original Mechanism",
  "False Necessity Inference",
  "Spurious Simplification",
  "Constraint Drop",
  "Invariant Preservation Bias",
  "Failure Under Distribution Shift",
  "Mode Collapse Reasoning",
  "Surface Similarity Trap"
]

GENERATE_SCHEMA = {}

FILTER = f"""You are a strict scientific benchmark filter for the subject area: {config.subject}. Your task is to evaluate a multiple-choice scientific reasoning question.

The question has 4 reasoning paths (A–D). Exactly one is structurally consistent with the mechanism. The others are intended to be structurally flawed but locally plausible.

Your task is NOT to solve the question. Your task is to evaluate structural symmetry and tension quality.

------------------------------------------------------------
INPUT
------------------------------------------------------------

- question
- mechanism_summary
- structural_tension_anchor
- reasoning_paths (A–D)

------------------------------------------------------------
EVALUATION CRITERIA
------------------------------------------------------------

1. Local Plausibility Symmetry
For each path:
- Is it internally coherent?
- Does it avoid obvious logical jumps?
- Does it avoid extreme language cues (e.g., strictly, necessarily, entirely)?
- Does it avoid trivial contradiction?

If one path is clearly more polished or more stable → false.
Otherwise → true.

------------------------------------------------------------

2. Structural Complexity Balance

Compare paths on:
- number of requires used
- number of invariants referenced
- number of failure_modes referenced
- reasoning chain depth

If one path is structurally deeper or more comprehensive → false.
Otherwise → true.

------------------------------------------------------------

3. Divergence Node Check

Determine whether:
- All paths diverge at the same structural decision point.

If divergence occurs at unrelated places → false.
Otherwise → true.

------------------------------------------------------------

4. Structural Failure Tension Check

Verify:
- Do at least two reasoning paths handle a structural boundary differently?
- Is there a clear structural tension around a constraint or stability condition?
- Is the correct path resolving that tension differently from at least one incorrect path?

If no real structural boundary is being contested → false.

------------------------------------------------------------

5. Structural Constraint Engagement

Definition:
A question has structural constraint engagement if at least two reasoning paths handle a meaningful mechanism boundary or constraint differently, and the correct path resolves this boundary coherently.

Evaluation Logic:

1. Identify whether a clear structural boundary exists (e.g., capacity–interference tradeoff, invariant limit, failure boundary).
2. Check whether at least two reasoning paths explicitly or implicitly treat this boundary differently.
3. Verify that the correct path resolves the boundary through constraint-consistent reasoning rather than surface plausibility.

Return:
- true  → if genuine structural tension exists.
- false → if no meaningful boundary is contested or if all paths operate in the same logic space.

------------------------------------------------------------

6. Dominance Cue Detection

Is the correct path visibly more cautious, more nuanced, or more globally consistent in a way that makes it stand out?

------------------------------------------------------------

OUTPUT FORMAT (STRICT JSON ONLY)
------------------------------------------------------------

```json
{{
  "local_symmetry": true / false,
  "complexity_balance": true / false,
  "divergence_valid": true / false,
  "structural_tension": true / false,
  "structural_constraint_engagement": true / false,
  "dominance_cue_detected": true / false,
  "critical_issue": "short explanation"
}}
```"""

FILTER_SCHEMA = {
  "type": "object", 
  "requires": ["local_symmetry", "complexity_balance", "divergence_valid", "structural_tension", "structural_constraint_engagement", "dominance_cue_detected", "critical_issue"],
  "properties": {
      "local_symmetry": {"type": "boolean"},
      "complexity_balance": {"type": "boolean"},
      "divergence_valid": {"type": "boolean"},
      "structural_tension": {"type": "boolean"},
      "structural_constraint_engagement": {"type": "boolean"},
      "dominance_cue_detected": {"type": "boolean"},
      "critical_issue": {"type": "string", "minLength": 1},
  },
  "additionalProperties": False
}

MINITEST = f"""You are an expert on {config.subject}. You are given a scientific reasoning question with 4 reasoning paths (A–D).

Do NOT deeply analyze structural consistency. Instead, choose the option that appears MOST PLAUSIBLE on first-pass reasoning. If none of these options are plausible, please choose "E. None of the above is plausible".

------------------------------------------------------------
INPUT
------------------------------------------------------------

- question
- reasoning_paths (A–D)

------------------------------------------------------------
OUTPUT FORMAT
------------------------------------------------------------

```json
{{
  "selected_option": "A | B | C | D | E",
  "explanation": "..."
}}
```
"""

MINITEST_SCHEMA = {
  "type": "object",
  "required": ["selected_option", "explanation"],
  "properties": {
      "selected_option": {"type": "string", "enum": EXPAND_OPTIONS + [NOT_ANSWERABLE]},
      "explanation": {"type": "string", "minLength": 1}
  },
  "additionalProperties": False
}

REVERSE_CONSISTENCY = f"""You are a strict scientific benchmark filter for the subject area: {config.subject}. You are evaluating structural constructability of reasoning paths.

You are given:

- A mechanism summary
- A question
- Three reasoning paths (A–C)

For EACH reasoning path independently:

Assume the reasoning path is correct.

Your task:
Determine whether it is possible to construct a logically consistent mechanism, fully compatible with the question stem and mechanism summary, that would make this reasoning path internally valid.

Important:

- Do NOT judge which option is actually correct.
- Do NOT compare paths.
- Evaluate each path independently.
- A path is "constructable" only if no internal contradiction with preserved invariants, stated requirements, or tested failure modes is unavoidable.

If the path requires violating preserved invariants, ignoring tested failure modes, or contradicting the question setup, then it is NOT constructable.

------------------------------------------------------------
EVALUATION CRITERIA
------------------------------------------------------------

For each path check:

1. Internal Logical Coherence
2. Compatibility with preserved invariants
3. No unavoidable triggering of forbidden failure_modes
4. No contradiction with the scenario described in the question
5. Does not rely on undefined or fabricated assumptions

------------------------------------------------------------
OUTPUT FORMAT (STRICT JSON)
------------------------------------------------------------

```json
{{
  "A": {{
    "constructable": true / false,
    "reason": "short explanation"
  }},
  "B": {{
    "constructable": true / false,
    "reason": "short explanation"
  }},
  "C": {{
    "constructable": true / false,
    "reason": "short explanation"
  }}
}}
```"""

REVERSE_CONSISTENCY_USER = """
------------------------------------------------------------
Mechanism Summary
------------------------------------------------------------

{unit}

------------------------------------------------------------
Question
------------------------------------------------------------

{q}

------------------------------------------------------------
Reasoning Paths
------------------------------------------------------------

{options}"""

REVERSE_CONSISTENCY_SCHEMA = {
    "type": "object",
    "required": ['A', 'B', 'C'],
    "properties": {
        x: {
            "type": "object",
            "required": ["constructable", "reason"],
            "properties": {
                "constructable": {"type": "boolean"},
                "reason": {"type": "string", "minLength": 1}
            },
            "additionalProperties": False
        }
        for x in ['A', 'B', 'C']
    },
    "additionalProperties": False
}

VALID = f"""You are a strict scientific benchmark filter for the subject area: {config.subject}. Your task is to evaluate the intrinsic quality of a question.

Input: 
A single question only.

You must evaluate the following four criteria independently:

1. language_reasonableness
2. non_triviality
3. unambiguity
4. no_semantic_redundancy

For each criterion:
- Output true or false.
- Provide structured reasoning steps explaining how you reached the conclusion.
- Your reasoning must follow the defined evaluation logic below.

-----------------------------------
Evaluation Logic Definitions
-----------------------------------

(1) language_reasonableness

Definition:
The question must be grammatically valid, syntactically coherent, and semantically interpretable.

Evaluation Steps:
- Step 1: Check for grammatical completeness (subject, predicate, logical connectors).
- Step 2: Check for internal logical consistency (no contradictory constraints inside the question).
- Step 3: Check for semantic interpretability (a well-defined task is being requested).
If any step fails → false.
Otherwise → true.

(2) non_triviality

Definition:
The question should require non-obvious reasoning or structural inference.

Evaluation Steps:
- Step 1: Determine if the answer can be retrieved by direct recall of a single common fact.
- Step 2: Determine if the question can be solved via pattern-matching without reasoning.
- Step 3: Determine whether solving requires combining at least two constraints, logical steps, or structural reasoning.
If Steps 1 or 2 are true AND Step 3 is false → trivial → false.
Otherwise → true.

(3) unambiguity

Definition:
The question must have a single clearly defined interpretation and answer space.

Evaluation Steps:
- Step 1: Identify all possible interpretations.
- Step 2: Check if multiple interpretations lead to different valid answers.
- Step 3: Check if key terms are underspecified.
If ambiguity affects answer determinability → false.
Otherwise → true.

(4) no_semantic_redundancy

Definition:
The question should not contain duplicated constraints that do not increase structural difficulty.

Evaluation Steps:
- Step 1: Identify repeated semantic constraints.
- Step 2: Determine if removing duplicated information changes difficulty.
If duplicated constraints exist and do not change reasoning path → false.
Otherwise → true.

-----------------------------------

Output format (strict JSON):

```json
{{
  "language_reasonableness": {{
    "decision": true | false,
    "explanation": "..."
  }},
  "non_triviality": {{
    "decision": true | false,
    "explanation": "..."
  }},
  "unambiguity": {{
    "decision": true | false,
    "explanation": "..."
  }},
  "no_semantic_redundancy": {{
    "decision": true | false,
    "explanation": "..."
  }}
}}
```
"""

VALID_SCHEMA = {
    "type": "object",
    "properties": {
        x: {
            "type": "object",
            "properties": {
                "decision": {"type": "boolean"},
                "explanation": {"type": "string", "minLength": 1}
            },
            "required": ["decision", "explanation"],
            "additionalProperties": False
        }
        for x in ["language_reasonableness", "non_triviality", "unambiguity", "no_semantic_redundancy"]
    },
    "required": ["language_reasonableness", "non_triviality", "unambiguity", "no_semantic_redundancy"],
    "additionalProperties": False
}

VALID_TENSION = f"""You are a strict structural diagnostic evaluator for the subject area: {config.subject}.  

Input:
- A single question. The question contains a predefined list: tested_failure_modes (guaranteed non-empty at schema level).

Your task is to determine whether the question genuinely activates those failure modes.

Evaluate the following:

1. failure_mode_activation
2. structural_tension_present
3. error_pattern_distinctness

-----------------------------------
Evaluation Logic Definitions
-----------------------------------

(1) failure_mode_activation

Definition:
Each tested_failure_mode must be structurally required for correct solving.

Evaluation Steps:
- Step 1: Identify each tested_failure_mode.
- Step 2: For each failure mode, check whether a solver who ignores that failure mode would likely fail.
- Step 3: If a failure mode can be bypassed without affecting success → not activated.
If all tested_failure_modes are structurally necessary → true.
Otherwise → false.

(2) structural_tension_present

Definition:
The question must contain at least two interacting constraints that create competing reasoning pressure.

Evaluation Steps:
- Step 1: Identify constraints.
- Step 2: Determine if constraints are independent or interacting.
- Step 3: Check whether satisfying one constraint increases complexity of satisfying another.
If interaction exists → true.
If constraints are additive but non-interacting → false.

(3) error_pattern_distinctness

Definition:
Different incorrect reasoning paths should produce distinguishable answer types.

Evaluation Steps:
- Step 1: Enumerate plausible incorrect reasoning strategies.
- Step 2: Determine whether these produce distinguishable outputs.
- Step 3: If most wrong paths collapse to same shallow error → not distinct.
If at least two distinct systematic error patterns exist → true.

-----------------------------------

Output format (strict JSON):

```json
{{
  "failure_mode_activation": {{
    "decision": true | false,
    "explanation": "..."
  }},
  "structural_tension_present": {{
    "decision": true | false,
    "explanation": "..."
  }},
  "error_pattern_distinctness": {{
    "decision": true | false,
    "explanation": "..."
  }}
}}
```"""

VALID_TENSION_SCHEMA = {
    "type": "object",
    "properties": {
        x: {
            "type": "object",
            "properties": {
                "decision": {"type": "boolean"},
                "explanation": {"type": "string", "minLength": 1}
            },
            "required": ["decision", "explanation"],
            "additionalProperties": False
        }
        for x in ["failure_mode_activation", "structural_tension_present", "error_pattern_distinctness"]
    },
    "required": ["failure_mode_activation", "structural_tension_present", "error_pattern_distinctness"],
    "additionalProperties": False
}

TEST = f"""You are an expert on {config.subject}. You are asked to answer the following multiple-choice question.

If you determine that:
- the assumptions are internally contradictory,
- the question cannot be meaningfully adjudicated given its stated assumptions,
- or the question is ill-posed as a scientific query,

you MUST select option {NOT_ANSWERABLE}: "None of the above. / This question is unanswerable".

Otherwise, select the single best answer.

Explain your reasoning step by step. Output the selected option letter and the reasoning steps in the following JSON format:

```json
{{ 
  "selected_answer": "A" | "B" | "C" | "D" | "E",
  "reasoning_steps": "..."
}}
```
"""

TEST_SCHEMA = {
  "type": "object",
  "required": ["selected_answer", "reasoning_steps"],
  "properties": {
      "selected_answer": {"type": "string", "enum": EXPAND_OPTIONS + [NOT_ANSWERABLE]},
      "reasoning_steps": {"type": "string", "minLength": 1}
  },
  "additionalProperties": False
}

WRONG_ANSWER = """You are a strict structural diagnostic evaluator for the subject area: {subject}. You are evaluating reasoning traces of incorrect answers in a scientific benchmark.

Your task is ONLY to classify each incorrect reasoning trace into one of two categories:

1. structure_error
2. execution_error

------------------------------------------------------------
DEFINITIONS
------------------------------------------------------------

STRUCTURE_ERROR:

A structural reasoning deviation that reflects a systematic misinterpretation 
of the mechanism specification. It must involve incorrect reasoning about at least one of:

- requires
- invariants
- produces
- failure_modes

A structure_error MUST be mapped to exactly ONE primary error pattern 
from the predefined ERROR_PATTERN_SET.

A reasoning trace qualifies as structure_error if:

- The core inferential step depends on a flawed structural assumption.
- Removing the flawed structural assumption would invalidate the conclusion.
- The reasoning exhibits a coherent but incorrect causal interpretation.


EXECUTION_ERROR:

A non-structural mistake occurring despite correct understanding of the mechanism.

Examples include:

- Arithmetic or symbolic manipulation mistakes
- Logical slip in multi-step deduction
- Misreading numeric conditions
- Accidental omission of a constraint despite acknowledging it earlier
- Internal inconsistency not tied to a conceptual misunderstanding

Execution_error does NOT represent a systematic misinterpretation 
of mechanism structure.


------------------------------------------------------------
PRIMARY ERROR PATTERN SELECTION (for structure_error only)
------------------------------------------------------------

ERROR_PATTERN_SET = {error_pattern_set}

For structure_error:

- Select exactly ONE primary_pattern.
- The selected pattern must be the DOMINANT structural cause of failure.
- If multiple patterns appear, choose the one without which the reasoning would not hold.
- If no dominant structural cause exists, classify as execution_error.


------------------------------------------------------------
INPUT
------------------------------------------------------------

The inputs are the question structure and a list of incorrect answers, each containing:

- model_id
- selected_option_statement
- reasoning_steps

------------------------------------------------------------
OUTPUT FORMAT (STRICT JSON ONLY)
------------------------------------------------------------

```json
{{
  "error_analysis": [
    {{
      "model_id": "M1",
      "classification": "structure_error" | "execution_error",
      "primary_pattern": "..." | null,
      "justification": "Short explanation of why this classification was chosen"
    }}
  ]
}}
```

------------------------------------------------------------
IMPORTANT
------------------------------------------------------------

- Evaluate each reasoning trace independently.
- Base your decision strictly on the reasoning_trace.
- Do not evaluate question quality.
- Do not aggregate across answers.
- Do not suggest rejection.
- Output JSON only.
"""
# - intended_error_pattern (the pattern originally assigned to that option)

WRONG_ANSWER_USER = """
------------------------------------------------------------
Question
------------------------------------------------------------

{q}

------------------------------------------------------------
Incorrect Answers
------------------------------------------------------------

{content}"""


def WRONG_ANSWER_SCHEMA(num_errors):
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["error_analysis"],
        "properties": {
            "error_analysis": {
                "type": "array",
                "minItems": num_errors,
                "maxItems": num_errors,
                "prefixItems": [
                    {
                        "type": "object",
                        "additionalProperties": False,
                        "required": ["model_id", "classification", "primary_pattern", "justification"],
                        "properties": {
                            "model_id": {"const": f"M{i + 1}"},
                            "classification": {"type": "string", "enum": ["structure_error", "execution_error"]},
                            "primary_pattern": {"anyOf": [{"type": "string", "enum": ERROR_PATTERN_SET}, {"type": "null"}]},
                            "justification": {"type": "string", "minLength": 1}
                        }
                    }
                    for i in range(num_errors)
                ],
                "items": False
            }
        }
    }


RIGHT_ANSWER = f"""You are a structural reasoning annotator for the subject area: {config.subject}. You are given:

- A multiple-choice question
- Several model reasoning traces that reached the correct answer

Your task is to analyze reasoning only based on the question text.

------------------------------------------------------------
TASK

For EACH reasoning trace, classify the reasoning type and depth.

------------------------------------------------------------

STEP 1 — Identify Structural Conditions

From the question, identify explicit structural conditions:
- stated assumptions
- constraints
- boundary conditions
- causal relationships
- logical dependencies

Ignore background descriptions.

------------------------------------------------------------

STEP 2 — Analyze Reasoning Dependency

Determine how many structural conditions are actively used in the reasoning. A reasoning is:

1. structural_joint_reasoning
   - Uses at least TWO structural conditions
   - These conditions form a logical dependency chain
   - Removing one condition would invalidate the conclusion

2. partial_structural_reasoning
   - Mentions multiple conditions
   - But only one is essential for the conclusion
   - Or reasoning chain is weak / loosely connected

3. shortcut_or_surface_reasoning
   - Relies on only one condition
   - Uses general knowledge or pattern matching
   - Uses elimination strategy
   - Does not meaningfully depend on question structure

------------------------------------------------------------

STEP 3 — Reasoning Depth

Label reasoning depth:

- shallow: single-step mapping or direct recall
- moderate: two-step reasoning
- deep: multi-step chained reasoning with intermediate inferences

------------------------------------------------------------

IMPORTANT RULES

- Do NOT judge whether the question is good or bad.
- Do NOT mention mechanism terms.
- Do NOT infer unstated assumptions.
- Evaluate strictly based on observable reasoning text.

------------------------------------------------------------

OUTPUT FORMAT (STRICT JSON)

```json
{{
  "analysis": [
    {{
      "model_id": "M1",
      "reasoning_type": "structural_joint_reasoning" | "partial_structural_reasoning" | "shortcut_or_surface_reasoning",
      "reasoning_depth": "shallow" | "moderate" | "deep",
      "justification": "Explain why this classification is assigned"
    }}
  ]
}}
```
"""

RIGHT_ANSWER_USER = """
------------------------------------------------------------
Question
------------------------------------------------------------

{q}

------------------------------------------------------------
Correct Answers
------------------------------------------------------------

{content}"""


def RIGHT_ANSWER_SCHEMA(num_rights):
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["analysis"],
        "properties": {
            "analysis": {
                "type": "array",
                "minItems": num_rights,
                "maxItems": num_rights,
                "prefixItems": [
                    {
                        "type": "object",
                        "additionalProperties": False,
                        "required": ["model_id", "reasoning_type", "reasoning_depth", "justification"],
                        "properties": {
                            "model_id": {"const": f"M{i + 1}"},
                            "reasoning_type": {"type": "string", "enum": ["structural_joint_reasoning", "partial_structural_reasoning", "shortcut_or_surface_reasoning"]},
                            "reasoning_depth": {"type": "string", "enum": ["shallow", "moderate", "deep"]},
                            "justification": {"type": "string", "minLength": 1}
                        }
                    }
                    for i in range(num_rights)
                ],
                "items": False
            }
        }
    }


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
  "explanation": "..."
}
```
"""

REVISE_SCHEMA = {
  "type": "object",
  "required": ["question", "options", "answer", "explanation"],
  "properties": {
    "question": {"type": "string", "minLength": 1},
    "options": {
      "type": "object",
      "required": EXPAND_OPTIONS,
      "properties": {k: {"type": "string", "minLength": 1} for k in EXPAND_OPTIONS},
      "additionalProperties": False
    },
    "answer": {"type": "string", "enum": EXPAND_OPTIONS},
    "explanation": {"type": "string"}
  },
  "additionalProperties": False
}
