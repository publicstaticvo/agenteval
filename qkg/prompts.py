GENERATE = """You are an expert research scientist in materials science. Your task is to generate THREE multiple-choice questions that can be answered using ONLY the information explicitly stated or logically implied in the question itself.

CRITICAL REQUIREMENT:
A well-trained scientist should be able to eliminate all incorrect options by carefully reading the question alone, WITHOUT needing to recall specific data, figures, or unstated results from the paper.

Each question must satisfy ALL of the following:

1. Question construction
- The question must include concrete, checkable conditions (e.g., material pairing, bias polarity, contact asymmetry, measurement outcome).
- These conditions must directly rule out incorrect options.
- Do NOT include vague qualifiers such as “high-quality”, “as observed”, “in experiments”, or “as reported”.
- The question must not rely on hidden facts that only appear in the paper.

2. What the question may test
- Causal exclusion: which explanations are incompatible with the stated conditions?
- Conditional reasoning: which mechanism works ONLY under the given configuration?
- Logical consistency: which interpretation does NOT introduce extra assumptions?

3. Prohibited question styles
- Do NOT ask “What is the primary reason/mechanism for X?” unless competing mechanisms are explicitly constrained by the question.
- Do NOT ask questions whose answer depends on numerical values, band diagrams, or material parameters not stated.
- Do NOT test recall of canonical facts.

4. Options
- Provide exactly FOUR answer options (A–D).
- Exactly ONE option must be correct.
- Each incorrect option must fail because it assumes something NOT stated in the question.
- No option may be correct in the absence of the question stem.

5. Answer & Explanation
- Explain why the correct option follows directly from the question conditions.
- Explain why each incorrect option requires an additional unsupported assumption.
- Do NOT reference the paper, experiments, or prior literature.

Output ONLY in the following JSON format:
```json
{
  "questions": [
    {
      "question": "...",
      "options": {
        "A": "...",
        "B": "...",
        "C": "...",
        "D": "..."
      },
      "answer": "A" | "B" | "C" | "D",
      "explanations": "..."
    }
  ]
}
```
"""

QUESTION_SCHEMA = {
  "type": "object",
  "required": ["question", "options", "answer", "explanations"],
  "properties": {
    "question": {"type": "string", "minLength": 1},
    "options": {
      "type": "object",
      "required": ['A', 'B', 'C', 'D'],
      "properties": {k: {"type": "string", "minLength": 1} for k in ['A', 'B', 'C', 'D']}
    },
    "answer": {"type": "string", "enum": ['A', 'B', 'C', 'D']},
    "explanations": {"type": "string"}
  }
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

FILTER = """You are a strict scientific benchmark filter. Your task is to decide whether the given multiple-choice question should be eliminated because answering it would require access to paper-specific details rather than scientific reasoning.

A question MUST be eliminated if correct answering requires:
- Referring to a specific figure, table, equation, or section
- Recalling exact numerical values, sample labels, or device configurations
- Remembering experimental conditions not stated in the question
- Concluding "insufficient information is given" as the main reasoning step

A question MUST be retained if it can be answered through:
- Logical consequences of stated assumptions
- Conceptual reasoning about physical mechanisms
- Comparing competing interpretations
- High-level domain knowledge without paper recall

Output ONLY in JSON format:

```json
{
  "eliminate": true | false,
  "reason": "brief explanation"
}
```
"""

REVISE = """You are an expert scientific question designer. You are given a well-formed multiple-choice question with 4 options and a single correct answer. Your task is to rewrite the question so that it has EXACTLY TEN answer options (A–J), while remaining a SINGLE-ANSWER multiple-choice question.

PRIMARY OBJECTIVE:
Increase option diversity while minimizing redundancy, independent correctness, and question-irrelevant answer options.

STRICT CONSTRAINTS:

1. Preserve the Core Question
- Do NOT change what is being asked.
- Do NOT introduce new physical mechanisms, materials, or experimental paradigms.

2. Correct Option
- The correct option must remain correct for the SAME reason.
- It must require at least one explicit condition from the question stem to be true.

3. Incorrect Options — Structured Generation
When expanding from 4 to 10 options, follow this distribution:
- At least FOUR options must explicitly reference a condition or regime stated in the question stem.
- At most TWO options may invoke general mechanisms without question-specific qualifiers.
- At most ONE option may involve idealized or limiting-case assumptions.

4. Prohibited Patterns
- Do NOT create paraphrases or near-synonyms.
- Do NOT include both a mechanism and its direct consequence as separate options.
- Do NOT include options that would be correct in most similar systems.

5. Reasoning Depth Control
- Each option must hinge on exactly ONE unstated assumption.
- Avoid multi-branch or conditional reasoning.

6. Redundancy Check (Self-check)
Before finalizing:
- Verify that removing any single option does NOT leave another option that says the same thing.
- Verify that no option is obviously true or false without using the question stem.

OUTPUT FORMAT (JSON ONLY):
```json
{
  "question": "...",
  "options": {
    "A": "...",
    "B": "...",
    "C": "...",
    "D": "...",
    "E": "...",
    "F": "...",
    "G": "...",
    "H": "...",
    "I": "...",
    "J": "..."
  },
  "answer": "A" | "B" | "C" | "D" | "E" | "F" | "G" | "H" | "I" | "J",
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
      "required": ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J'],
      "properties": {k: {"type": "string", "minLength": 1} for k in ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J']},
      "additionalProperties": False
    },
    "answer": {"type": "string", "enum": ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J']},
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

CANONICAL = """You are an expert on material science. You are given an answer option from a scientific multiple-choice question. Rewrite the option into a canonical form that:
- States only the core claim being asserted
- Removes rhetorical phrasing, examples, and hedging
- Does NOT add assumptions from the question stem

Output format:
```json
{
  "canonical_statement": "one concise declarative sentence"
}
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
                "enum": ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J']
            }
        },
        "trivially_false_without_question": {
            "type": "array",
            "items": {
                "type": "string", 
                "enum": ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J']
            }
        },
        "does_not_depend_on_question": {
            "type": "array",
            "items": {
                "type": "string", 
                "enum": ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J']
            }
        },
        "redundant_options": {
            "type": "array",
            "items": {
                "type": "array",
                "minItems": 2,
                "items": {
                    "type": "string",
                    "enum": ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J']
                }
            }
        }    
    }
}

TEST = """You are an expert on material science. You are asked to answer the following multiple-choice question.

If you determine that:
- the assumptions are internally contradictory,
- the question cannot be meaningfully adjudicated given its stated assumptions,
- or the question is ill-posed as a scientific query,

you MUST select option K: "None of the above. / This question is unanswerable".

Otherwise, select the single best answer.

Do NOT explain your reasoning. Output only the selected option letter, in the following JSON format:

```json
{ "selected_answer": "A" | "B" | "C" | "D" | "E" | "F" | "G" | "H" | "I" | "J" | "K" }
```
"""

TEST_SCHEMA = {
  "type": "object",
  "required": ["selected_answer"],
  "properties": {"selected_answer": {"type": "string", "enum": ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K']}},
  "additionalProperties": False
}
