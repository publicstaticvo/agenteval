GENERATE = """You are an expert research scientist in materials science.

Your task is to generate THREE multiple-choice questions that are implicitly or explicitly resolved by the provided academic paper. Each question must reflect a specific scientific judgment that becomes decidable ONLY under the concrete conditions stated in the question stem.

CRITICAL DESIGN OBJECTIVE:
The correct answer MUST rely on at least one explicit condition described in the question.
If the question were removed or generalized, the correct answer should no longer be obviously true.

Each question must satisfy ALL of the following:

1. Question construction
- The question must be answerable using the reasoning, evidence, or interpretation presented in the paper.
- The question must include at least one explicit condition, regime, comparison, or configuration (e.g., material pairing, bias polarity, interface structure, measurement context).
- Removing or altering this condition should make the answer ambiguous or debatable.
- The question must be understandable on its own and must NOT reference the paper, figures, or sections.

2. Prohibited question styles
- Do NOT ask purely canonical or textbook-style questions.
- Avoid questions phrased as “What is the primary reason/mechanism for X?” unless the mechanism is valid ONLY under the stated conditions.
- Do NOT ask questions whose correct answer would remain true in most closely related systems.

3. Options
- Provide exactly FOUR answer options (A–D).
- Exactly ONE option must be correct.
- Incorrect options must correspond to realistic alternative interpretations that would require additional assumptions NOT guaranteed by the stem.
- No option may be correct without explicitly using information from the question stem.

4. Answer & Explanation
- Clearly indicate the correct option letter.
- Explain why the correct option follows specifically from the stated conditions.
- Explain why the other options fail when those same conditions are applied.
- Do NOT explain answers by appealing to general textbook knowledge alone.

Important constraints
- Do NOT artificially increase difficulty.
- Do NOT introduce rare, pathological, or contrived scenarios.
- Keep reasoning depth shallow: each option should hinge on at most ONE unstated assumption.

Output ONLY in the following JSON format:

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
