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
      "properties": {
        "A": {"type": "string", "minLength": 1},
        "B": {"type": "string", "minLength": 1},
        "C": {"type": "string", "minLength": 1},
        "D": {"type": "string", "minLength": 1}
      }
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
  }
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

ASSUMPTION = """You are a research scientist analyzing the logical structure of a scientific argument. You are given a single multiple-choice question that has a correct answer. Your task is to identify the implicit scientific assumptions or preconditions that must hold for the correct answer to remain valid.

For each assumption:
- The assumption must already be implicitly relied upon in the question's reasoning.
- The assumption must NOT introduce new data or external information.
- The assumption should be something that, if violated, would plausibly change the correct answer.

Examples of valid assumptions:
- A specific transport regime applies (e.g., diffusive vs ballistic)
- A commonly used approximation is valid
- A background effect is negligible
- A scaling relation holds over the relevant range

Output ONLY in JSON format:

```json
{
  "implicit_assumptions": [
    "Assumption 1",
    "Assumption 2"
  ]
}
```
"""

SCIENTIFIC_SIGNIFICANCE = """You are a senior research scientist. You are given:

1) a multiple-choice question,
2) its correct answer,
3) a list of implicit assumptions supporting that answer.

Your task is to rewrite the QUESTION STEM ONLY so that answering it requires judging whether the original conclusion remains valid under the stated assumptions.

Constraints:
- Do NOT change the underlying physical mechanism.
- Do NOT change the correct answer.
- Do NOT add new variables, data, or parameters.
- The question should ask the solver to assess robustness, validity, or justification of a conclusion.

Examples of acceptable reframing:
- Assessing whether a conclusion is justified under stated assumptions
- Determining which interpretation is most robust
- Judging whether a commonly used inference is scientifically warranted

Do NOT:
- Expand the number of options
- Turn the question into an open-ended discussion
- Ask about novelty or future work

Output ONLY the rewritten QA in JSON format with the SAME options and answer:

```json
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
      "properties": {
        "A": {"type": "string", "minLength": 1},
        "B": {"type": "string", "minLength": 1},
        "C": {"type": "string", "minLength": 1},
        "D": {"type": "string", "minLength": 1},
        "E": {"type": "string", "minLength": 1},
        "F": {"type": "string", "minLength": 1},
        "G": {"type": "string", "minLength": 1},
        "H": {"type": "string", "minLength": 1},
        "I": {"type": "string", "minLength": 1},
        "J": {"type": "string", "minLength": 1}
      }
    },
    "answer": {"type": "string", "enum": ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J']},
    "explanations": {"type": "string"}
  }
}

REVISE = """You are an expert scientific question designer. You are given a multiple-choice question with FOUR options and a known correct answer. Your task is to expand the options to EXACTLY TEN choices (A–J).

Rules:
- Preserve the original correct option unchanged in meaning.
- Introduce additional options that reflect:
  - partially correct reasoning
  - assumptions valid only in other regimes
  - mechanisms that are plausible but incompatible with the question's premises
- Do NOT increase difficulty by adding artificial multi-step logic.
- Each incorrect option should fail for a specific, identifiable reason.

Output ONLY the reframed QA in the following JSON format:

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
  "explanations": "Explain both the technical reasoning AND why this choice supports or rejects the broader scientific interpretation.."
}
"""

CRITIC = """You are a senior human researcher acting as a meta-critic for scientific research questions. Your task is to assess whether the following multiple-choice question could plausibly have been written by a human researcher for a real research discussion, rather than being artificially constructed by an automated pipeline.

You are given a single multiple-choice question (with 10 options plus one "None of the above"). You must perform the following evaluation steps:

1. Solve the given question
- Solve the question by choosing the correct answer from the options.
- If you choose the option K (None of the above / This question is not answerable), mark the question as AI-LIKE.

2. Identify the Core Research Judgment
- In one or two sentences, state the core scientific judgment this question is asking the solver to make.
- This judgment should be expressible without equations, numbers, or mechanism enumeration.
- If you cannot clearly articulate such a judgment, mark the question as AI-LIKE.

3. Assess Naturalness of the Question
Determine whether this question satisfies ALL of the following:
- A human researcher could naturally ask this question in a group meeting, peer review, or informal discussion.
- The question arises from skepticism, caution, or boundary-checking, rather than from a desire to increase difficulty.
- The question does not rely on a long list of explicit assumptions to justify its existence.

If any of these are violated, mark the question as AI-LIKE.

4. Evaluate the Role of the Correct Answer
Determine whether the correct answer is:
- The most restrained and least overconfident interpretation among the options.
- The option that avoids unnecessary extrapolation beyond the given information.
- The option that a careful reviewer would select to avoid making an unjustified scientific claim.

If the correct answer is instead:
- The most technically elaborate,
- The most mechanism-rich,
- Or the one that simply chains together the most facts,

mark the question as AI-LIKE.

5. Check for Artificial Difficulty Signals
Assess whether the question shows signs of artificial construction, including:
- Excessive symmetry among options.
- Overly clean separation between “textbook-correct” and “textbook-wrong” answers.
- Difficulty arising primarily from option proliferation rather than judgment subtlety.

If such signals are present, mark the question as AI-LIKE.

6. Final Verdict
Based on the above, output a final judgment.

Output STRICTLY in the following JSON format:

```json
{
  "selected_answer": "A" | "B" | "C" | "D" | "E" | "F" | "G" | "H" | "I" | "J" | "K",
  "core_scientific_judgment": "...",
  "could_a_human_naturally_ask_this": true | false,
  "is_the_correct_answer_the_most_restrained": true | false,
  "signs_of_artificial_difficulty": true | false,
  "overall_assessment": "HUMAN-LIKE" | "AI-LIKE",
  "justification": "A concise explanation grounded in scientific reasoning culture, not model behavior."
}
```
"""

CRITIC_SCHEMA = {
  "type": "object",
  "required": [
      "selected_answer", 
      "core_scientific_judgment", 
      "could_a_human_naturally_ask_this",
      "is_the_correct_answer_the_most_restrained",
      "signs_of_artificial_difficulty",
      "overall_assessment",
      "justification"
  ],
  "properties": {
    "selected_answer": {"type": "string", "enum": ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K']},
    "core_scientific_judgment": {"type": "string", "minLength": 1},
    "could_a_human_naturally_ask_this": {"type": "boolean"},
    "is_the_correct_answer_the_most_restrained": {"type": "boolean"},
    "signs_of_artificial_difficulty": {"type": "boolean"},
    "overall_assessment": {"type": "string", "enum": ['HUMAN-LIKE', 'AI-LIKE']},
    "justification": {"type": "string"}
  },
  "additionalProperties": False
}
