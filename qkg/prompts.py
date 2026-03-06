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
   - Necessary: Ci is required for the argument supporting TP. If Ci were removed, the paper’s reasoning for TP would fail or become unsupported.
   - Supporting: Ci contributes to the reasoning for TP but is not strictly required. Removing Ci would weaken the argument but TP could still plausibly hold.
   - Irrelevant: Ci does not play a meaningful role in supporting TP. Removing Ci would not affect whether TP holds.
3. Provide a short reasoning for each classification (1-2 sentences, optional).

Output Format (JSON):

```json
[
  {
    "id": "C1",
    "dependency_type": "necessary / supporting / irrelevant",
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
                "dependency_type": {'enum': ['necessary', 'supporting', 'irrelevant']},
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
B. The proposition does not hold.
C. The proposition holds only in a weakened or limited form.
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

FILTER = """You are a strict question filter. Your task is to verify whether a multiple-choice question satisfies structural validity requirements.

The question follows a fixed semantic answer framework:

A — The Target Proposition still holds.
B — The Target Proposition fails.
C — The Target Proposition only partially holds.
D — It cannot be determined from the given information.

You must NOT attempt to solve the question or judge its scientific validity. Your task is only to check whether the question structure is valid.

Evaluate the following aspects:

------------------------------------------------
1. Option Semantic Compliance
------------------------------------------------

Check whether each option correctly matches the intended semantic meaning.

Valid forms:

A — clearly states that the Target Proposition still holds.
B — clearly states that the Target Proposition fails or no longer holds.
C — clearly states that the Target Proposition only partially holds, weakens, or holds in a limited way.
D — clearly states that the outcome cannot be determined from the provided information.

Mark an issue if:

- An option expresses a different meaning.
- The wording contradicts the intended semantic category.
- The meaning is unclear or inconsistent with the framework.

Issue type: "invalid_option_semantics"

------------------------------------------------
2. Option Distinctness
------------------------------------------------

Check whether the four options are semantically distinct.

Mark an issue if:

- Two or more options express essentially the same meaning.
- The difference between options is trivial or unclear.

Issue type: "ambiguous_option"

------------------------------------------------
3. External References
------------------------------------------------

Check whether the question relies on information outside the provided text.

Mark an issue if the question refers to:

- figures, tables, or sections of the original paper
- "the method proposed in the paper"
- unnamed algorithms or mechanisms not defined in the question
- experimental results not included in the question
- dataset-specific or paper-specific terminology that is not explained

Issue type: "external_reference"

------------------------------------------------
4. Missing Information
------------------------------------------------

Check whether the question provides enough information to interpret the counterfactual scenario.

Mark an issue if:

- the perturbation is unclear
- key concepts are undefined
- the Target Proposition cannot be evaluated without additional context

Issue type: "missing_information"

------------------------------------------------

If the question has no issues, return an empty list.

Output format:

```json
{
  "issues": [
    {
      "issue_type": "...",
      "reason": "..."
    }
  ]
}
```

Allowed issue types:

- invalid_option_semantics
- ambiguous_option
- external_reference
- missing_information
"""

FILTER_SCHEMA = {
  "type": "object", 
  "requires": ["issues"],
  "properties": {
      "issues": {
          "type": "array",        
          "items": {
              "type": "object",
              "additionalProperties": False,
              "required": ['issue_type', 'reason'],
              "properties": {
                  "issue_type": {"enum": ["invalid_option_semantics", "ambiguous_option", "external_reference", "missing_information"]},
                  'reason': {"type": "string", "minLength": 1}
              }
          }
      }
  },
  "additionalProperties": False
}
