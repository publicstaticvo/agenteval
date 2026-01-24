GENERATE = """You are an expert research scientist in material science. Your task is to extract or create THREE challenging and difficult, self-contained question–answer pairs from the provided academic paper. The QAs will be used as exam questions for PhD students and must be clear, extremely challenging, and context-independent, i.e., understandable on its own without referring back to the original paper.

Each QA pair must include:

1. Question:
- A clear, difficult, and standalone question.
- The question must include sufficient background information or context so that one can fully understand and attempt it without referring to the original paper.
- Define any abbreviations, notation, or domain-specific terminology used.
- DO NOT use phrases like “according to the paper” or “the proposed method.”
- The question should be complex enough to require deep understanding of the subject.
- It should engage **advanced reasoning**, such as: Conceptual analysis, Theoretical or mathematical derivations, Methodological design, Causal reasoning or hypothesis testing, etc.

2. Options:
- Provide exactly four answer choices.
- Only one option should be correct.
- The three incorrect options should be plausible but clearly wrong upon careful reasoning, ideally derived by subtly altering the logic or assumptions behind the correct answer.

3. Answer: 
- The correct option letter.

4. Rationale:
- A detailed explanation of why the correct answer is correct and why each incorrect option is wrong.
- DO NOT reference the original paper in any part of the rationale.
- If calculations are required, include the full step-by-step process.

**Important:**
- Questions must be self-contained, including any necessary context or definitions.
- Do not reference the original paper in any part of the question, options, or rationale.
- Aim for PhD-level difficulty, testing understanding of key technical ideas.
- Ensure that only one option is unambiguously correct.

Pleaes prepare your QA pairs in the following JSON format only:

```json
{
  "questions": [
    {
      "question": "question 1",
      "options": {
        "A": "...",
        "B": "...",
        "C": "...",
        "D": "..."
      },
      "answer": "A" | "B" | "C" | "D",
      "explanations": "..."
    }, 
    ...
  ]
}
```
"""

GENERATE_SCHEMA = {
  "type": "object",
  "required": ['questions'],
  "properties": {
    "questions": {
      "type": "array",
      "item": {
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
    }
  }
}

FILTER = """You are a strict filter for scientific benchmark questions.

Your task is to determine whether a given question should be ELIMINATED because it requires either:

(1) fine-grained recall of specific experimental details, numerical values, device configurations, figures, tables, or sections from a paper, OR
(2) external references or background knowledge beyond what is explicitly stated in the question itself.

A question SHOULD be eliminated if answering it correctly would require:
- referring to a specific figure, table, equation, or section
- recalling exact experimental setups, measurement conditions, or numeric values
- knowing facts not explicitly stated in the question
- judging that \"insufficient information is given\" as the main reasoning step

A question SHOULD NOT be eliminated if it can be answered by:
- conceptual reasoning
- qualitative comparison
- logical consequences of stated assumptions
- high-level scientific understanding without recalling paper-specific details

Output in JSON format ONLY:

{
  "eliminate": true | false,
  "reason": "brief explanation"
}
"""

REVISE = """You are an expert research scientist in material science. Your task is to refine the provided multiple-choice question to increase its difficulty and test deeper reasoning appropriate for PhD-level understanding. 

The input is a JSON object including a question, answer options, an answer, and an explanation for the answer. Use the provided answer and explanation for reference, they may be incorrect.

**Refinement Goals:**

1. Expand Options with Subtle Variations 
- Rewrite the answer options to include 10 choices labeled A–J.
- All options should seem plausible to someone with partial knowledge, but only one should be fully correct. Introduce subtle numerical or conceptual variations among options.

2. Remove Surface-Level Hints
- Eliminate obvious formulas, definitions, or axioms from the question.
- Assume the solver must recall or derive them independently. You may include these concepts in the solution rationale, but not in the question.

3. Increase Reasoning Depth
- Replace direct or few-step problems with multi-step (>3) or causal reasoning.
- Use reasoning chains (e.g., X leads to Y, which leads to Z, which explains W) or require intermediate inferences without giving all variables.

4. Rephrase to Introduce Diversity
- Use varied question formats: causal, hypothetical, comparative, inferential, conditional, etc.
- Maintain clarity and scientific rigor while diversifying expression.

5. Reframe for Scientific Significance
- Rewrite the question so that it emphasizes a general scientific reasoning pattern,
  methodological assumption, or physical mechanism that could recur across multiple studies,
  rather than being tied to a single experimental instance.
- The question should resemble the type of reasoning a researcher would perform
  when synthesizing insights across several papers (e.g., in a review or meta-analysis),
  even though it remains answerable from the given context.
- Do NOT introduce new experimental facts, external literature, or domain knowledge
  beyond what is logically implied in the original question.
- Preserve the original correct answer.

**Important:**
- The refined question must still admit exactly one unambiguously correct option.
- Do NOT turn the question into an open-ended, speculative, or future-work question.
- Do NOT ask about novelty, significance, or research directions explicitly.
- If reframing for scientific significance risks making multiple options defensible, revert to a more conservative abstraction level.

Please only output the refined QA in the following JSON format: 

```json
{
  "question": "question 1",
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
# - Each refined question should challenge deep understanding of core technical concepts, appropriate for advanced graduate-level assessment.
# - The refined question must remain solvable using information provided or generally assumed background knowledge in the domain. Avoid ambiguity or underspecified problems.
# - Ensure that only one option is unambiguously correct.
# - If the original question is poorly written, ambiguous, or lacks depth, you may create a new question based on the same underlying concept or topic reflected in the provided QA.

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

SCIENTIFIC_SIGNIFICANCE = """You are a senior research scientist and review author in material science.

Your task is NOT to increase technical difficulty, and NOT to change the multiple-choice format. Instead, you must reframe the question so that answering it requires assessing the SCIENTIFIC SIGNIFICANCE of the phenomenon, mechanism, or trend described.

The input is a refined multiple-choice question (10 options, single correct answer) that already tests deep technical reasoning.

Your reframing MUST satisfy ALL of the following constraints:

1. Preserve Technical Core
- Do NOT change the underlying physical mechanism, equations, or reasoning chain.
- The correct option must remain correct for the same technical reason.

2. Introduce Research-Level Stakes
- Explicitly connect the question to at least ONE of the following:
  a) validity of a commonly used experimental proxy or metric
  b) generalizability across materials / systems / studies
  c) justification (or invalidation) of a broader scientific claim
  d) implications for whether a research direction is worth pursuing

3. Shift Perspective from “Explanation” to “Judgment”
- The question should ask the solver to judge whether a conclusion, interpretation, or practice is scientifically justified, not merely to explain why an effect occurs.

4. Preserve Solvability
- The question must remain solvable using the information given and generally assumed background knowledge.
- Do NOT introduce new parameters, data, or unstated assumptions.

5. Minimal Surface Changes
- Prefer modifying the question stem rather than rewriting options.
- Options may be lightly reworded ONLY if necessary to align with the new framing.

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

TEST = """You are an expert on material science. Please answer the following problem by selecting the best option you think.

Explain your reasoning then output your final answer. Your final answer should strictly follow this format: $\\boxed{answer}$, for example, $\\boxed{A}$."""

# You should first provide your answer in this format: $\\boxed{answer}$, then explain your reasoning below.

CRITIC = """You are an independent expert reviewer evaluating whether the following multiple-choice question truly tests SCIENTIFIC SIGNIFICANCE, rather than only technical correctness.

You are given a single multiple-choice question (10 options) and must:

1. Answer the question.
2. Explicitly state:
   - What higher-level scientific claim, practice, or research decision this question is implicitly testing.
3. Judge whether the question meaningfully constrains that claim.

If the question can be answered purely as a technical exercise without engaging with its broader scientific implications, mark it as "INSUFFICIENT SIGNIFICANCE".

Output in the following JSON format:

```json
{
  "selected_answer": "A" | "B" | "C" | "D" | "E" | "F" | "G" | "H" | "I" | "J" | "K",
  "scientific_claim_under_test": "...",
  "does_the_question_constrain_this_claim": true | false,
  "justification": "..."
}
```
"""

CRITIC_SCHEMA = {
  "type": "object",
  "required": ["selected_answer", "scientific_claim_under_test", "does_the_question_constrain_this_claim", "justification"],
  "properties": {
    "selected_answer": {"type": "string", "enum": ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K']},
    "scientific_claim_under_test": {"type": "string", "minLength": 1},
    "does_the_question_constrain_this_claim": {"type": "boolean"},
    "justification": {"type": "string"}
  },
  "additionalProperties": False
}
