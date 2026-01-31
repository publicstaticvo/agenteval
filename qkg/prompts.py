GENERATE = """You are an expert research scientist in materials science. Your task is to identify and formulate THREE multiple-choice questions that are already implicitly or explicitly answered by the provided academic paper. These questions must reflect the kinds of scientific questions that the paper itself resolves, clarifies, or settles through its experiments, analysis, or arguments.

Each question must satisfy ALL of the following:

1. Question construction:
- The question must be answerable based on the scientific reasoning or evidence presented in the paper.
- The question should reflect a real scientific uncertainty that the paper addresses (e.g., mechanism identification, interpretation choice, validity of an assumption).
- The question must be understandable on its own, without referring to the paper text.
- Provide sufficient background context in the question so that the problem is well-posed.

2. Options:
- Provide exactly FOUR answer options (A–D).
- Exactly one option must be correct.
- Incorrect options should correspond to realistic alternative interpretations, mechanisms, or assumptions that a researcher might reasonably consider.

3. Answer:
- Indicate the correct option letter.

4. Explanation:
- Explain why the correct option follows from the stated assumptions and reasoning.
- Explain why the other options fail under the same assumptions.
- Do NOT reference the paper, figures, or sections explicitly.

Important constraints:
- Do NOT artificially increase difficulty.
- Do NOT require multi-step derivations unless they are intrinsic to the scientific reasoning.
- Avoid exam-style tricks or contrived logic.

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

REVISE = """You are an expert scientific question designer. You are given a well-formed multiple-choice question with 4 options and a single correct answer. Your task is to rewrite the question so that it has EXACTLY 10 answer options (A–J), while remaining a SINGLE-ANSWER multiple-choice question.

PRIMARY OBJECTIVE:
Maximize the likelihood that the rewritten question passes subsequent structural assumption checks.

STRICT CONSTRAINTS:

1. Preserve the Core Question
- Do NOT change the question stem.
- Do NOT change what is being asked.
- Do NOT introduce new physical mechanisms, effects, materials, or experimental paradigms.

2. Option Construction Principles
- All 10 options must be plausible under SOME explicit or implicit assumptions.
- The correct option must remain correct for the SAME underlying reason as in the original question.
- Each incorrect option should be wrong because it relies on an additional assumption that is NOT guaranteed by the question stem.

3. How to Generate Additional Options (from 4 to 10)
You may create new options by:
- Restricting applicability to a special regime or condition
- Extending a claim beyond its justified scope
- Assuming idealized or limiting cases
- Assuming the absence or presence of a secondary effect already mentioned in the question

Do NOT create options by:
- Introducing new variables not mentioned or implied
- Violating basic physical or logical consistency
- Relying on extremely rare, pathological, or contrived scenarios

4. Reasoning Depth Control
- Do NOT force long or multi-branch reasoning chains.
- Each option should be assessable by checking whether its required assumptions are supported by the question stem.
- Avoid chaining more than one additional assumption per option.

5. Scientific Significance (Light Touch Only)
- You MAY phrase options in a way that reflects interpretation or judgment (e.g., “can be reasonably attributed to…”).
- Do NOT explicitly discuss novelty, research directions, or field-wide implications.

OUTPUT FORMAT (JSON ONLY):

{
  "question": "...",
  "options": {
    "A": "...",
    "B": "...",
    ...
    "J": "..."
  }
  "answer": "A" | "B" | "C" | "D" | "E" | "F" | "G" | "H" | "I" | "J",
  "explanations": "..."
}

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
{
  "self_contradictory": true | false,
  "reason": "brief explanation"
}
"""

REDUNDANT = """You are a strict scientific benchmark filter. You are given a scientific multiple-choice question. Your task is to judge whether the question stem contains information that:
- Is not required to determine the correct answer, AND
- Does not meaningfully function as a distractor for any option.

Instructions:
- Do NOT assume perfect exam design.
- Only flag information that is clearly irrelevant to all options.
- If unsure, answer "no".

Output format:
{
  "contains_redundant_information": true | false,
  "reason": "brief explanation"
}
"""

IMPLAUSIBLE = """You are a strict scientific benchmark filter. You are given a scientific question. Your task is to judge whether the combination of assumptions described in the question is considered:
- Extremely atypical, or
- Violating well-established physical or scientific principles.

Instructions:
- Judge the combination of assumptions, not individual statements.
- Do NOT require absolute impossibility; extreme implausibility is sufficient.
- Ignore purely hypothetical or philosophical framing.

Output format:
{
  "physically_implausible": true | false,
  "reason": "brief explanation"
}
"""

CANONICAL = """You are an expert on material science. You are given an answer option from a scientific multiple-choice question. Rewrite the option into a canonical form that:
- States only the core claim being asserted
- Removes rhetorical phrasing, examples, and hedging
- Does NOT add assumptions from the question stem

Output format:
{
  "canonical_statement": "one concise declarative sentence"
}
"""

WITHOUT_QUESTION = """You are an expert on material science. You are given an answer option WITHOUT the question. Your task is to judge whether the truth value of this statement can be determined based solely on general scientific knowledge or common facts.

Instructions:
- Assume no additional context.
- If the statement clearly requires missing conditions or context, answer "cannot_determine".

Output format:
{
  "judgment": "true" | "false" | "cannot_determine",
  "reason": "brief explanation"
}
"""

DEPENDS_ON_QUESTION = """You are an expert on material science. You are given a question and an answer option. Your task is to judge whether evaluating this option requires information provided in the question.

Instructions:
- If the option can be judged without referencing the question, answer "no".
- If any part of the question is necessary, answer "yes".

Output format:
{
  "depends_on_question": "yes" | "no",
  "reason": "brief explanation"
}
"""

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
