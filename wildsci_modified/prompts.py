from config import Config
config = Config.from_yaml("config.yaml")
OPTIONS = ['A', 'B', 'C', 'D', 'E']
EXPAND_OPTIONS = ['A', 'B', 'C', 'D', 'E']
NOT_ANSWERABLE = "F"
# ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J']

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
