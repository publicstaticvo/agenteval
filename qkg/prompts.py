from config import Config
config = Config.from_yaml("config.yaml")
OPTIONS = ['A', 'B', 'C', 'D']
EXPAND_OPTIONS = ['A', 'B', 'C', 'D']
NOT_ANSWERABLE = "E"
# ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J']

PAPERCLASS = """You are a senior research scientist. You are given metadata of a research paper. Your task is to classify the paper’s PRIMARY contribution orientation into EXACTLY ONE of the following categories:

A. Mechanistic / Causal Explanation
   The paper explains an underlying mechanism, causal structure, or process responsible for a phenomenon.

B. Theoretical Derivation
   The paper derives formal results, theorems, mathematical principles, or analytic characterizations.

C. Empirical Phenomenon Explanation
   The paper identifies and explains a reproducible empirical phenomenon through structured analysis.

D. System / Framework Performance
   The paper proposes a system, framework, or method and demonstrates improved effectiveness or performance.

E. Benchmark / Evaluation Report
   The paper introduces datasets, benchmarks, metrics, or comparative evaluation studies.

F. Survey / Review
   The paper synthesizes existing literature, summarizes progress, or organizes prior work.

G. Normative / Policy
   The paper makes recommendations, ethical arguments, governance proposals, or societal guidance.

---

INPUT FIELDS:
- Title
- Abstract

---

INSTRUCTIONS:

1. Base your classification primarily on the Abstract.
2. If the Abstract is missing, use Title + Introduction excerpt.
3. If both Abstract and Introduction are missing, classify using Title only and mark confidence as "low".
4. If insufficient information is available to determine contribution type, output "unknown".
5. Choose EXACTLY ONE category (A–G).
6. Do NOT output multiple categories.
7. Focus on the PRIMARY contribution, not secondary elements.

---

OUTPUT FORMAT:

```json
{
  "paper_type": "A | B | C | D | E | F | G | unknown",
  "justification": "1–3 sentences explaining why this category is primary."
}
```"""

PAPERCLASS_SCHEMA = {
    "type": "object",
    "properties": {
        "paper_type": {'enum': ['A', 'B', 'C', 'D', 'E', "F", 'G', 'unknown']},
        "justification": {"type": "string", "minLength": 1}
    },
    "required": ['paper_type', 'justification'],
    "additionalProperties": False
}

KNOWLEDGE = f"""You are a senior research scientist in {config.subject}. Your task is to extract the theoretical mechanism structure of a paper.

You should extract structural elements that are explicitly or implicitly required for the main claim to hold.

---

Extract the following components:

### 1. Target Proposition

Extract exactly ONE Target Proposition.

The Target Proposition must satisfy:

- It states the primary explanatory, theoretical, or causal claim advanced by the paper.
- It identifies what mechanism, principle, or structural relationship the paper establishes.
- It is not merely a claim about performance improvement or system effectiveness.
- If this proposition were false, the paper would lose its core explanatory or theoretical contribution (not merely its empirical advantage).

It must NOT be:
- A definition
- A taxonomy
- A descriptive summary
- A performance comparison
- A system demonstration
- A policy recommendation

≤ 35 words.

If no valid Target Proposition satisfying all conditions can be identified, return an empty object.

### 2. Structural Commitments

Extract 2-6 Structural Commitments.

Definition:
A Structural Commitment is an explicit research design or framing decision adopted in the paper that constrains how the Target Proposition is established, tested, or interpreted.
It must constrain the explanatory or inferential logic that supports the Target Proposition.
It must not merely describe implementation choices whose alteration would affect performance but not the explanatory structure.

Each Structural Commitment must:

- Be an explicit research design, framing, or methodological decision.
- Constrain how the Target Proposition is established or evaluated.
- Be stated in a way that is specific to the study.

Examples include:
- Choice of theoretical framework or model class
- Specification of methodological approach
- Experimental or empirical design setup
- Data selection criteria or sampling regime
- Analytical or statistical assumptions required for inference
- Measurement or evaluation protocol
- Operationalization of key constructs
- Boundary conditions explicitly imposed
- Computational, physical, or experimental constraints adopted by the study

Do NOT extract:
- Definitions of terms
- Widely accepted background knowledge
- Descriptive statements about the field
- Purely historical context
- Normative or ethical recommendations
- High-level societal predictions
- Generic statements that could apply to most studies

If there's no Target Proposition, or no enough valid Structural Constraints satisfying all conditions can be identified, return an empty object.

---

Output Format (Please output JSON Only):

```json
{{
  "target_proposition": "...",
  "structural_commitments": [
    {{
      "id": "C1",
      "statement": "..."
    }},
    {{
      "id": "C2",
      "statement": "..."
    }},
    ...
  ]
}}
```

Or 

```json
{{}}
```

if no valid Target Proposition or Structural Commitment satisfying all conditions can be identified.
"""

KNOWLEDGE_SCHEMA = {
  "type": "object",
  "properties": {
    "target_proposition": {"type": "string", "minLength": 1},
    "structural_commitments": {
      "type": "array",
      "minItems": 2,
      "maxItems": 6,
      "items": {
        "type": "object",
        "properties": {"statement": {"type": "string", "minLength": 1}},
        "required": ["id", "statement"],
        "additionalProperties": False
      },
      "prefixItems": [
        {"properties": {"id": {"const": "C1"}}},
        {"properties": {"id": {"const": "C2"}}},
        {"properties": {"id": {"const": "C3"}}},
        {"properties": {"id": {"const": "C4"}}},
        {"properties": {"id": {"const": "C5"}}},
        {"properties": {"id": {"const": "C6"}}}
      ]
    }
  },
  "required": ["target_proposition", "structural_commitments"],
  "additionalProperties": False
}

KNOWLEDGE_FILTER = """You are a strict scientific benchmark filter. You are evaluating extracted mechanism units and detect semantic-level issues.

A mechanism unit is expected to contain:
- a target proposition
- fixed facts
- structural commitments

Return a JSON object:

```json
{
  "target_proposition_issues": [...],
  "structural_commitment_issues": [...]
}
```

Each issue must include:

{
  "id": "...",  # required for structural commitment issues
  "problem": "...",  # MUST choose from given problem marks
  "reason": "..."
}

If no issue exists in a category, return an empty list.

---

# Evaluation Rules

---

## 1. Target Proposition Check

For the Target Proposition:

1. Determine whether it is a genuine proposition.
   Mark as "not_a_proposition" if it is:
   - A definition
   - A taxonomy
   - A descriptive summary
   - A normative recommendation
   - A background statement

2. Determine whether it is central to the paper’s objective.
   Mark as "not_primary_contribution" if the statement expresses a claim, but it does not represent the primary contribution of the paper. It may be:
   - A supporting result
   - A side finding
   - A methodological detail
   - A contextual claim

3. Mark as "performance_claim" if the proposition primarily asserts improved effectiveness, accuracy, or capability of a system without identifying a mechanism or principle.

---

## 2. Structural Commitment Checks

For each structural commitment:

1. Mark as "misclassified_background" if the statement describes background knowledge, commonly accepted facts, or general characteristics of the field rather than a design decision adopted by the study.
   (e.g. Reinforcement learning models describe how agents learn from feedback.)

2. Mark as "generic_statement" if the statement is too general or abstract to represent a concrete research design decision.
   (e.g. Evaluation must be rigorous and fair.)

3. Mark as "duplicated_semantics" if two or more structural commitments express substantially overlapping content or restate the same design decision in different wording.

4. Mark as "peripheral_design" if the statement describes an implementation detail or secondary procedural choice that does not materially constrain how the Target Proposition is established.
   (e.g. Training was performed for 100 epochs.)

# 3. Validity Checks

For each extracted item (Target Proposition or Structural Commitment):

Check whether it is structurally self-contained.

1. Mark as "reference_dependency" if it contains explicit references to the original paper.
   (e.g., "Figure 2", "Section 4", "Table 1", "as shown above")

2. Mark as "underspecified_entity" if it refers to entities using placeholders without minimal description and does not clarify their general nature.
   (e.g., "our method", "this approach", "the model")

3. Mark as "other_invalidity" if it cannot be understood as a standalone research statement without access to the original paper.

---

# Important Constraints

- Do not judge scientific correctness.
- Do not suggest rewrites.
- Do not compress content.
- Do not enforce structural limits.
- Do not apply keyword-based heuristics.
- Use semantic reasoning only.

Return only JSON.
"""

KNOWLEDGE_FILTER_SCHEMA = {
  "type": "object",
  "required": ["target_proposition_issues", "structural_commitment_issues"],
  "properties": {
    "target_proposition_issues": {
        "type": "array",        
        "items": {
            "type": "object",
            "additionalProperties": False,
            "required": ['problem', 'reason'],
            "properties": {
                "problem": {"enum": ["not_a_proposition", "not_primary_contribution", 'performance_claim', "duplicated_semantics", "reference_dependency", "underspecified_entity", "other_invalidity"]},
                'reason': {"type": "string", "minLength": 1}
            }
        }
    },
    "structural_commitment_issues": {
        "type": "array",        
        "items": {
            "type": "object",
            "additionalProperties": False,
            "required": ['id', 'problem', 'reason'],
            "properties": {
                "id": {"type": "string", "pattern": r"^C\d+$"},
                "problem": {"enum": ["misclassified_background", "generic_statement", "peripheral_design", "duplicated_semantics", "reference_dependency", "underspecified_entity", "other_invalidity"]},
                'reason': {"type": "string", "minLength": 1}
            }
        }
    }
  },
  "additionalProperties": False
}

KNOWLEDGE_CLASS = """You are a senior research scientist. You are given a Target Proposition (TP) and a list of Structural Commitments (C1, C2, ..., Cn) from a scientific paper. 
Your task is to determine the dependency of each Structural Commitment on the Target Proposition.

Rules:

1. Evaluate each Ci individually.
2. Classify the dependency as one of the following:
   - Necessary: Removing Ci would make TP fail or unsupported.
   - Peripheral: TP would largely still hold without Ci; Ci only provides minor support.
   - Sufficient: Ci alone can ensure TP holds under some context.
   - Auxiliary: Ci has indirect or partial influence, not strictly necessary or sufficient.
3. Provide a short reasoning for each classification (1-2 sentences, optional).

Output Format (JSON):

```json
[
  {
    "id": "C1",
    "dependency_type": "necessary / peripheral / sufficient / auxiliary",
    "reasoning": "Optional, concise explanation for classification."
  },
  ...
]
```
"""


def KNOWLEDGE_CLASS_SCHEMA(origin):
    return {
        "type": "array", 
        "minItems": len(origin),
        "maxItems": len(origin),
        "items": {
            "type": "object",
            "properties": {
                "dependency_type": {'enum': ['necessary', 'peripheral', 'sufficient', 'auxiliary']},
                "reasoning": {'type': 'string', 'minLength': 1}
            },
            'required': ['id', 'dependency_type', 'reasoning'],
            'additionalProperties': False
        },
        'prefixItems': [{"properties": {"id": {"const": x['id']}}} for x in origin]
    }


PERTURB = """You are a senior research scientist. You are given:

* A Target Proposition (TP)
* A single Structural Commitment (SC)

Your task is to construct four structural perturbations of the given SC.

Construct the following four perturbations:

---

## Operator 1 — Structural Modification

Modify the given Structural Commitment (SC) while preserving its general topic, but altering its structural strength or scope.

You must explicitly select one modification type:

* Weakening
* Strengthening
* Boundary Instantiation
* Parameter Change

### Definitions

- **Weakening**
  Replace the commitment with a strictly weaker, more limited, or more permissive version that reduces its structural constraint.

- **Strengthening**
  Replace the commitment with a strictly stronger, more restrictive, or more demanding version that increases its structural constraint.

- **Boundary Instantiation**
  Replace the commitment with an extreme, edge-case, or limiting-instance version of itself (e.g., minimal scale, maximal scale, degenerate case).

- **Parameter Change**
  Modify a specific variable, threshold, or configuration parameter inside the commitment while preserving the overall structure.

Rules:

* Do not introduce new structural commitments.
* Do not modify the Target Proposition.
* Keep the modification local to the given SC.
* The modified SC must remain logically coherent.
* Clearly state the modification type.

Output:

* Modification Type
* Modified Commitment Statement
* Minimal Counterfactual Scenario (1–2 sentences describing how TP may change)

---

## Operator 2 — Inversion

Reverse or negate the core directional logic of the Structural Commitment.

Definition:

Replace the commitment with a version that flips its causal, logical, or dependency direction.

This may include:

* Reversing necessity into dispensability
* Reversing causal direction
* Replacing enabling condition with inhibiting condition
* Reversing optimization objective

Rules:

* Do not modify the Target Proposition.
* Only invert the internal logic of the given SC.
* The inverted commitment must remain structurally meaningful (not trivial negation like “not X” unless logically substantive).

Output:

* Inverted Commitment Statement
* Minimal Counterfactual Scenario (1–2 sentences describing how TP may fail or reverse)

---

## Output Format (JSON Only)

```json
{
  "perturbations": [
    {
      "type": "structural_modification",
      "modification_type": "weakening" | "strengthening" | "boundary_instantiation" | "parameter_change",
      "statement": "...",
      "minimal_counterfactual_scenario": "..."
    },
    {
      "type": "inversion",
      "statement": "...",
      "minimal_counterfactual_scenario": "..."
    }
  ]
}
```
"""

PERTURB_SCHEMA = {
    "type": "object",
    "properties": {
        "perturbations": {
            "type": "array",
            "prefixItems": [
                {
                    "type": "object",
                    "properties": {
                        "type": {"const": "structural_modification"},
                        "modification_type": {"enum": ["weakening", "strengthening", "boundary_instantiation", "parameter_change"]},
                        "statement": {"type": "string", "minLength": 1},
                        "minimal_counterfactual_scenario": {"type": "string", "minLength": 1}
                    },
                    "required": ["type", "modification_type", "statement", "minimal_counterfactual_scenario"],
                    "additionalProperties": False
                },
                {
                    "type": "object",
                    "properties": {
                        "type": {"const": "inversion"},
                        "statement": {"type": "string", "minLength": 1},
                        "minimal_counterfactual_scenario": {"type": "string", "minLength": 1}
                    },
                    "required": ["type", "statement", "minimal_counterfactual_scenario"],
                    "additionalProperties": False
                }
            ],
            "items": False,
            "minLength": 2,
            "maxLength": 2
        }
    },
    "required": ["perturbations"],
    "additionalProperties": False
}

GENERATE = """You are a formal scientific question constructor. You are given a scientific research scenario containing:

- A Target Proposition
- A set of Structural Commitments

Generate a single multiple-choice question that asks whether the proposition still holds under the described mechanism.

Requirements:

- Present the proposition clearly in the question.
- Describe the current mechanism completely in the question stem.
- Frame the situation as a self-contained scientific scenario.
- Do not explain or justify the answer.
- Output only the question and four answer options.

The four answer options must correspond to these meanings (rephrased naturally in context):

A. The proposition still holds as stated.
B. The proposition holds only in a weakened or limited form.
C. The proposition does not hold.
D. The outcome cannot be determined from the information given.

Output format (JSON only):

```json
{
  "question": "<one clearly written question paragraph>",
  "options": [
    {
      "id": "A",
      "statement": "...",
    },
    {
      "id": "B",
      "statement": "...",
    },
    {
      "id": "C",
      "statement": "...",
    },
    {
      "id": "D",
      "statement": "...",
    }
  ]
}
```
"""

GENERATE_SCHEMA = {
  "type": "object",
  "required": ["question", "options"],
  "properties": {
    "question": {"type": "string", "minLength": 1},
    "options": {
      "type": "array",
      "items": {
          "type": "object",
          "properties": {"statement": {"type": "string", "minLength": 1}},
          "required": ['id', 'statement'],
          'additionalProperties': False
      },
      'prefixItems': [{"properties": {"id": {"const": x}}} for x in OPTIONS],
      "minLength": len(OPTIONS),
      "maxLength": len(OPTIONS)
    }
  }
}

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
