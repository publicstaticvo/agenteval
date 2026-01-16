GENERATE_SYSTEM_1 = """You are an experienced AI research assistant and research task architecture expert. 
Your core responsibility is to analyze *reproducible experimental results* and their corresponding methods from research papers, 
and, in combination with available analytical tools, construct an actionable, logically rigorous, academically substantial research task with a comprehensive research plan.

🔴 [CORE REQUIREMENTS] 
- The research task must explicitly leverage the provided reproducible results and methods from the paper excerpt.
- Your research query must be sufficiently complex, academically profound, and scientifically valuable. 
- You must specify how to systematically employ exactly 3 different tools to investigate, simulate, or extend the research results.
- Each tool must be integrated in a phase-by-phase methodology explaining its role in realizing or validating the reproducible results.
"""

GENERATE_USER_1 = """
[AVAILABLE TOOLS]
{tools}

[REPRODUCIBLE RESULTS]
{result}

[METHODS]
{method}

Based on the above reproducible results and methods, construct a concrete, executable research task proposal.
🔴 [MANDATORY] You must precisely select and detail how to orchestrate exactly 3 available tools to complete this research.

Return in strict JSON format (JSON only, no other text):
{{
  "new_research_query": "Detailed, clear description of the research query and objectives",
  "required_tools": ["Tool A", "Tool B", "Tool C"],
  "research_scope_and_steps": "Phase-by-phase explanation of research scope, methodology, and specific logic of tool utilization",
  "evaluation_metrics": ["Metric 1", "Metric 2"]
}}"""

CRITIC_SYSTEM_1 = """You are a rigorous academic reviewer and evaluator specializing in scientific reasoning assessment.

🔴 [CRITICAL REQUIREMENTS]
- The research query must explicitly utilize exactly 3 different tools. If fewer or more than 3 tools are used, points must be significantly deducted.
- The proposed research task must remain scientifically consistent with the provided reproducible results.
- Any research objective, evaluation metric, or expected outcome that contradicts the given results should be treated as a major flaw.

Tool utilization and result consistency are the two highest-weight evaluation dimensions.
"""

CRITIC_USER_1 = """
[AVAILABLE TOOLS]
{tools}

[REPRODUCIBLE RESULTS]
{result}

[METHODS]
{method}

[RESEARCH TASK UNDER EVALUATION]
{query}

[TOOL USAGE INFORMATION]
Number of tools declared: {num_tools}
Specific tools: {tools_used}

Please conduct a rigorous evaluation based on the following five dimensions (Total: 100 points):

1. **Academic Rigor (0-20 points)**:
   - Is the research query clearly defined and scientifically precise?
   - Does it follow a valid scientific reasoning structure (objective → method → validation)?
   - Is terminology accurate and appropriate?

2. **Comprehensive Tool Utilization (0-30 points)** 🔴 [CORE DIMENSION]:
   - Base score of 20 points: Exactly 3 tools are used.
   - Additional 10 points: Quality and coherence of tool orchestration.
   - Are the roles of all 3 tools clearly specified and logically connected?

3. **Result Consistency and Faithfulness (0-25 points)** 🔴 [NEW CORE DIMENSION]:
   - Are the research objectives logically compatible with the provided reproducible results?
   - Could the proposed workflow plausibly reproduce, verify, or extend the given results?
   - Does the query avoid introducing unverifiable or contradictory claims?

4. **Feasibility (0-15 points)**:
   - Is the research task concrete and executable?
   - Are the steps sufficiently detailed to be followed in practice?
   - Are evaluation metrics measurable?

5. **Scientific Innovation and Practical Value (0-10 points)**:
   - Does the task go beyond trivial restatement of the results?
   - Does it meaningfully extend, analyze, or generalize the findings?

Return in strict JSON format (JSON only):
{{
  "total_score": <integer from 0-100>,
  "dimension_scores": {{
    "academic_rigor": <0-20>,
    "comprehensive_tool_utilization": <0-30>,
    "result_consistency_and_faithfulness": <0-25>,
    "feasibility": <0-15>,
    "scientific_innovation_and_practical_value": <0-10>
  }},
  "detailed_evaluation": "2-3 sentences of detailed analysis",
  "improvement_suggestions": "Concrete and actionable recommendations for improvement"
}}
"""

REVISE_SYSTEM = """You are an experienced AI research assistant and research task optimization expert.

Your responsibility is to revise an existing research task proposal based on:
(1) explicitly provided reproducible results and their corresponding methods,
(2) received critique and improvement suggestions,
while strictly preserving scientific consistency with the original reproducible results.

🔴 [CORE REQUIREMENTS]
- The revised research task must remain faithful to the given reproducible results and methods.
- You must NOT introduce objectives, hypotheses, or evaluation targets that contradict the provided results.
- The revised proposal must still employ exactly 3 different tools in a coherent and executable research pipeline.
- All revisions must directly respond to the received improvement suggestions.
"""

REVISE_USER = """
[AVAILABLE TOOLS]
{tools}

[REPRODUCIBLE RESULTS]
{result}

[METHODS]
{method}

[PREVIOUS RESEARCH TASK PROPOSAL]
{query}

[RECEIVED IMPROVEMENT SUGGESTIONS]
{critic}

Based on the improvement suggestions above, revise and optimize the previous research task proposal.
🔴 [MANDATORY CONSTRAINTS]
- The revised proposal must remain scientifically consistent with the provided reproducible results and methods.
- You must clearly explain how exactly 3 different tools are orchestrated to verify, simulate, or extend the given results.
- Do NOT introduce claims or objectives that cannot be supported by the given results.

Return in strict JSON format (JSON only, no other text):
{{
  "new_research_query": "Detailed and precise research query grounded in the given reproducible results",
  "required_tools": ["Tool A", "Tool B", "Tool C"],
  "research_scope_and_steps": "Phase-by-phase explanation of methodology and tool usage explicitly tied to the reproducible results",
  "evaluation_metrics": ["Metric 1", "Metric 2"]
}}
"""

SELECT_SYSTEM = """
You are a Scientific Data Engineer. Your goal is to prepare a "Reproduction Context" for a computational agent.
I will provide:
- Paper title
- Abstract
- Section titles (like "X. Title" or "X.Y. Title")
- The index and the first sentence of each paragraphs.

Task: Select 2 kind of paragraphs to form the context.
1. **The Goal Source:** Select the paragraphs that best defines *why* the research was done (usually Introduction).
2. **The Recipe Source:** Select the paragraphs that best defines *how* the computational experiments were performed.
   - Look for paragraphs in sections with these keywords: "Computational Details", "Methodology", "Simulation Setup", "Docking Protocol".
   - IGNORE paragraphs in sections like "Wet Lab", "Synthesis", or "Biological Assays" (our agent is purely computational).
   - IGNORE paragraphs in "Results" and "Discussion" (these contain outcomes we want the agent to *discover*, not read).

Output Format: JSON with keys "goal_paragraph_indexes" and "recipe_paragraph_indexes", each with a list of paragraph indexes:
```
{
   "goal_paragraph_indexes": [2],
   "recipe_paragraph_indexes": [6, 7]
}
```
"""

SELECT_USER = """
Paper Title: {title}
[Start of the Paper Abstract]
{abstract}
[End of the Paper Abstract]

[Start of the Paper Sections]
{text}
[End of the Paper Sections]
"""

HYBRID_SELECT_STEP_1 = """You are a Scientific Data Engineer. You are given the full text of a scientific paper.

Task:
Identify all sentences that MAY describe a reproducible experimental result or empirical finding.

Instructions:
- Only extract verbatim sentences from the paper.
- Do NOT judge correctness, reproducibility, or scientific value.
- Focus on sentences that state:
  * a concrete outcome,
  * a comparison,
  * a quantitative value,
  * a ranked or categorical conclusion,
  * or a clear empirical relationship.
- Exclude purely speculative, motivational, or background statements.
- Do NOT summarize or rewrite sentences.

Output:
Return a JSON object with the following structure:
```json
{
  "candidates": [
    {
      "paragraph_index": paragraph index (an integer),
      "sentence_text": "<verbatim sentence>"
    }
  ]
}
```
"""

HYBRID_SELECT_STEP_1_USER = """Full content of the paper:
{text}"""

HYBRID_SELECT_STEP_2 = """You are a Scientific Data Engineer. You are given:
1. One candidate experimental result sentence.
2. A limited evidence pool extracted from the paper, consisting only of nearby contextual sentences.

Your task is to determine whether the candidate sentence constitutes a reproducible experimental result.

Definition:
A reproducible experimental result must:
- State a concrete outcome that can be independently verified.
- Avoid purely subjective interpretation or author opinion.
- Be verifiable in principle without relying on unstated assumptions.

Important constraints:
- You MUST base your judgment ONLY on the provided evidence pool.
- You MUST NOT use any information outside the evidence pool.
- If evidence is insufficient, mark the result as not reproducible.

Output:
Return a JSON object with the following structure:

```json
{
  "reproducible": true | false,
  "reason": "<brief explanation (1–2 sentences)>",
  "supporting_sentences": ["Sentence 1", "Sentence 2", ...]
}
```

Additional rules:
- If "reproducible" is false, "supporting_sentences" MUST be an empty list.
- If "reproducible" is true, select AT MOST 3 supporting sentences.
- Supporting sentences MUST be copied verbatim from the evidence pool.
- Do NOT invent or paraphrase any content.
"""

HYBRID_SELECT_STEP_2_USER = """[Candidate sentence]
{text}

[Evidence pool]
{evidences}
"""

HYBRID_SELECT_STEP_3 = """You are a Scientific Data Engineer. You are given:
1. A reproducible experimental result sentence.
2. The structured full text of its source research paper.

Task:
1. Identify the minimal set of sentences that describe the experimental or analytical methods necessary to understand, contextualize, or generate research questions about the given result.
2. Determine what type of effort is required to reproduce this result.

Important rules:
- Only use information from the provided paragraphs. Do NOT look up outside sources.
- Only extract sentences that are directly relevant to how the result was obtained. Do NOT summarize, paraphrase, or invent information.
- Select a minimal number of method sentences (1–3 recommended).

Output:
Return a JSON object with the following structure:

{
  "method_sentences": ["Sentence 1.", "Sentence 2.", "Sentence 3."],
  "method_type": "wet" | "dry" | "hybrid" | "uncertain",
  "selection_reason": "<brief explanation of why these method sentences are relevant>"
}

Definitions of `method_type` classes:
- "wet": The result requires physical laboratory work (e.g., synthesis, biological assays, chemical reactions, material fabrication, in-vitro or in-vivo experiments).
- "dry": The result can be reproduced using computation, simulation, data analysis, or statistical evaluation only, without performing physical experiments.
- "hybrid": The result requires a combination of wet and dry procedures (e.g., experimental data generation followed by computational analysis).
- "uncertain": The provided text does not contain enough information to reliably classify the reproduction type.

If no method sentence is clearly relevant, return an empty "method_sentences" list.
"""

HYBRID_SELECT_STEP_3_USER = """[Reproducible experimental result]
{text}

[Paper structures]
{paper}
"""

GENERATE_SYSTEM = """
You are an experienced AI research assistant and research task architecture expert. Your core responsibility is to analyze *reproducible experimental results* and their corresponding methods extracted from research papers, and—using only the available analytical tools—construct a scientifically sound, executable research task.

This task will later be used in an agent-based evaluation environment, not as a standalone benchmark question.

🔴 [CORE PRINCIPLES]

1. Faithfulness:
   - The research task MUST be logically consistent with the provided reproducible results.
   - You MUST NOT restate, encode, or hard-copy any specific numerical values, ranges, deltas, thresholds, or exact measurements from the results.

2. Abstraction over Memorization:
   - Describe trends, relationships, mechanisms, or validation goals in qualitative or symbolic terms.
   - Numerical outcomes must be treated as *unknown targets to be investigated*, not as known constants.

3. Tool-Constrained Reasoning:
   - You MUST use exactly 3 tools from the provided tool list.
   - Each tool must play a distinct and necessary role in the proposed research workflow.

4. Evaluation-Aware Design:
   - In addition to the main research task, you MUST define a Probe Specification.
   - Probe Specification does NOT include answers.
   - Probe Specification defines *how the agent may be further questioned* to assess reasoning quality, tool alignment, and methodological soundness.

The output must be suitable for dynamic, interactive agent evaluation with no fixed answer key.
"""

GENERATE_USER = """
[AVAILABLE TOOLS]
{tools}

[REPRODUCIBLE RESULT (REFERENCE ONLY — DO NOT COPY NUMERICAL VALUES)]
{result}

[METHODS]
{method}

Based on the reproducible result and methods above, construct a concrete, executable research task proposal.

🔴 [MANDATORY REQUIREMENTS]

- Use EXACTLY 3 tools from the available tool list.
- Do NOT include any explicit numerical values from the result.
- The task must plausibly allow reproduction, validation, or extension of the referenced result.
- Define a Probe Specification that enables follow-up questioning without assuming a fixed correct answer.

Return in strict JSON format (JSON only, no other text).

Example output:
```json
{{
  "new_research_query": "A clear, high-level research objective phrased without copying numerical outcomes",
  "required_tools": ["Tool A", "Tool B", "Tool C"],
  "research_scope_and_steps": "Phase-by-phase explanation of the research workflow, explicitly mapping each phase to one or more tools",
  "evaluation_metrics": [
    "Qualitative or relative metric (no hard-coded numbers)",
    "Structural or comparative metric"
  ],
  "probe_spec": {{
    "probe_dimensions": [
      {{
        "name": "methodological_grounding",
        "description": "Probes whether the agent understands how the methods support the result",
        "example_probe_types": [
          "Justification of method selection",
          "Identification of necessary controls or baselines"
        ]
      }},
      {{
        "name": "tool_alignment",
        "description": "Probes whether the chosen tools are appropriate and correctly orchestrated",
        "example_probe_types": [
          "Role differentiation between tools",
          "Failure modes caused by tool misuse"
        ]
      }},
      {{
        "name": "robustness_and_generalization",
        "description": "Probes whether the agent can reason beyond a single experimental setting",
        "example_probe_types": [
          "Sensitivity analysis or alternative explanations",
          "Generalization to adjacent conditions or datasets"
        ]
      }}
    ]
  }}
}}
```
"""

CRITIC_SYSTEM = """
You are a rigorous academic evaluator specializing in agent-based scientific reasoning assessment.

You are NOT judging whether the agent reached the true numerical answer.
You ARE judging whether the proposed research task is:

- Faithful to the provided reproducible result
- Methodologically sound
- Tool-aligned
- Suitable for interactive, multi-step evaluation

🔴 [CRITICAL CONSTRAINTS]

- At least 3 tools must be used.
- Any appearance of copied numerical values from the reproducible result constitutes a MAJOR violation.
- Any research objective that contradicts or logically excludes the provided result constitutes a MAJOR violation.

Tool utilization and result faithfulness are the highest-weight dimensions.
"""

CRITIC_USER = """
[AVAILABLE TOOLS]
{tools}

[REPRODUCIBLE RESULT (REFERENCE)]
{result}

[METHODS]
{method}

[RESEARCH TASK UNDER EVALUATION]
{query}

Please conduct a rigorous evaluation based on the following five dimensions (Total: 100 points):

1. Academic Rigor (0–20 points)
   - Is the research objective clearly stated and scientifically meaningful?
   - Does the reasoning follow a valid objective → method → validation structure?

2. Tool Alignment and Orchestration (0–30 points) 🔴
   - Exactly 3 tools are used (base requirement).
   - Each tool has a distinct, justified role.
   - The tools form a coherent research pipeline.

3. Result Faithfulness and Non-Leakage (0–25 points) 🔴
   - The task is logically compatible with the provided result.
   - No explicit numerical values from the result appear in the task.
   - The task treats outcomes as targets to investigate, not given facts.

4. Feasibility and Executability (0–15 points)
   - The task can realistically be carried out using the specified tools.
   - The steps are sufficiently concrete.

5. Probe Specification Quality (0–10 points)
   - Probe dimensions are clearly defined.
   - Probes test reasoning quality rather than factual recall.
   - Probes enable multiple valid reasoning trajectories.

Return in strict JSON format (JSON only):

{{
  "total_score": <integer 0–100>,
  "dimension_scores": {{
    "academic_rigor": <0–20>,
    "tool_alignment_and_orchestration": <0–30>,
    "result_faithfulness_and_non_leakage": <0–25>,
    "feasibility_and_executability": <0–15>,
    "probe_specification_quality": <0–10>
  }},
  "detailed_evaluation": "Concise but precise justification of the score"
}}
"""
