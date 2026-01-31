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

ASSUMPTIONS = """You are a senior human researcher for scientific research questions. You are given a multiple-choice question with 10 options. Your task is to EXTRACT assumptions, NOT to evaluate them.

IMPORTANT CONSTRAINTS:
- You must NOT judge whether any assumption is correct, incorrect, or realistic.
- You must NOT infer which option is correct.
- You must NOT state or imply how many correct options exist.
- Treat all options symmetrically and blindly.

Your task consists of two parts:

PART 1: Global Assumptions
- Extract assumptions that are explicitly stated or unavoidably implied by the QUESTION STEM.
- These assumptions must be common to ALL options.
- Do NOT introduce background knowledge.
- Do NOT include assumptions that are specific to a particular option.

PART 2: Option-Specific Assumptions
- For EACH option, list additional assumptions that would need to hold for THAT OPTION to be true.
- These assumptions must be logically attributable to that specific option.
- Each assumption must clearly indicate which option it comes from.

Guidelines:
- If an option can be validated using only the global assumptions, output an empty list for that option.
- Do not merge assumptions across options, even if they sound similar.
- Use short, explicit, declarative statements.

Output only the following JSON structure:

```json
{
  "assumptions": [
    {
      "id": "P1",
      "option": "global",
      "statement": "..."
    },
    {
      "id": "P2",
      "option": "global",
      "statement": "..."
    },
    {
      "id": "A1",
      "option": "A",
      "statement": "..."
    },
    {
      "id": "B1",
      "option": "B",
      "statement": "..."
    }
  ]
}
```
"""

ASSUMPTION_SCHEMA = {
  "type": "object",
  "required": ["global_assumptions", "option_assumptions"],
  "properties": {
    "global_assumptions": {"type": "array", "items": {
      "type": "object",
      "required": ['id', 'statement'],
      "properties": {
        "id": {"type": "string", "minLength": 1},
        "statement": {"type": "string", "minLength": 1}
      },
      "additionalProperties": False
    }},
    "option_assumptions": {
      "type": "object",
      "required": ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J'],
      "properties": {
        k: {
          "type": "array",
          "items": {
            "type": "object",
            "required": ['id', 'statement'],
            "properties": {
              "id": {"type": "string", "minLength": 1},
              "statement": {"type": "string", "minLength": 1}
            },
            "additionalProperties": False
          }
        } 
        for k in ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J']
      },
      "additionalProperties": False
    }
  },
  "additionalProperties": False
}

GRAPH = """You are a senior human researcher acting as a meta-critic for scientific research questions. You are given a list of assumptions extracted from a multiple-choice question. Your task is to construct a STRUCTURAL ASSUMPTION GRAPH. Do NOT evaluate whether any assumption is true or false.

For EACH assumption, determine:

1. depends_on:
   - List other assumptions that must hold for this assumption to be meaningful.
   - If those assumptions fail, this assumption becomes ill-defined or meaningless.

2. mutual_exclusivity:
   - List assumptions that cannot be true at the same time as this one.

3. self_contradiction:
   - Set to true ONLY if the assumption contradicts itself internally.

IMPORTANT:
- Do NOT infer scientific correctness.
- Do NOT remove assumptions.
- Do NOT introduce new assumptions.

Output a JSON object where each key is an assumption ID:

```json
{
  "P1": {
    "depends_on": [],
    "mutual_exclusivity": [],
    "self_contradiction": false
  },
  "P2": {
    "depends_on": ["P1"],
    "mutual_exclusivity": ["P3"],
    "self_contradiction": false
  },
  ...
}
```
"""

GRAPH_SCHEMA = {
  "type": "object",
  "additionalProperties": {
    "type": "object",
    "required": ['depends_on', 'mutual_exclusivity', 'self_contradiction'],
    "properties": {
      "depends_on": {"type": "array", "items": {"type": "string", "minLength": 1}},
      "mutual_exclusivity": {"type": "array", "items": {"type": "string", "minLength": 1}},
      "self_contradiction": {"type": "boolean"}
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
