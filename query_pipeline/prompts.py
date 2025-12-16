GENERATE_SYSTEM = """You are an experienced AI research assistant and research task architecture expert. Your core responsibility is to analyze excerpts from research papers provided by users, and in combination with available analytical tools, construct an actionable, logically rigorous, academically substantial research task with a comprehensive research plan.

🔴 [CORE REQUIREMENTS] 
- Your research query must be sufficiently complex, academically profound, and scientifically valuable. 
- Your proposal must explicitly specify how to systematically employ at least 3 different tools to solve or explore the research query derived from the paper excerpt."""

GENERATE_USER = """
[AVAILABLE TOOLS]
{tools}

[ORIGINAL RESEARCH PAPER EXCERPT]
{text}

Based on the above paper excerpt, construct a concrete, executable research task proposal.
🔴 [MANDATORY] You must precisely select and detail how to orchestrate exactly 3 available tools to complete this research.

Return in strict JSON format (JSON only, no other text):
{{
  "new_research_query": "Detailed, clear description of the research query and objectives",
  "required_tools": ["Tool A", "Tool B", "Tool C"],
  "research_scope_and_steps": "Phase-by-phase explanation of research scope, methodology, and specific logic of tool utilization",
  "evaluation_metrics": ["Metric 1", "Metric 2"]
}}"""

CRITIC_SYSTEM = """You are a rigorous academic reviewer and evaluator.
🔴 [CRITICAL] The query must explicitly utilize at least 3 different tools. If fewer than 3 tools are used, points will be significantly deducted.
Tool utilization is the core evaluation dimension with the highest weight (0-35 points)."""

CRITIC_USER = """
[AVAILABLE TOOLS]
{tools}

[RESEARCH QUESTION UNDER EVALUATION]
{query}

[TOOL USAGE INFORMATION]
Number of tools declared: {num_tools}
Specific tools: {tools_used}

Please conduct a rigorous evaluation based on the following four dimensions (Total: 100 points):

1. **Academic Rigor (0-25 points)**:
   - Is the research query clearly defined and specific? Does it include quantifiable indicators?
   - Does it follow scientific methodology (hypothesis, methods, validation)?
   - Is terminology used accurately and appropriately?

2. **Comprehensive Tool Utilization (0-35 points)** 🔴 [CORE DIMENSION]:
   - Base score of 20 points: Must use 3 available tools
   - Additional 15 points: Based on quality of tool usage
   - Are the specific purposes of all 3 tools clearly articulated?
   - Do the tools form an organic research pipeline?

3. **Feasibility (0-30 points)**:
   - Is the research query concrete and actionable? Does it include clear steps or workflow?
   - Are the usage steps for all 3 tools clear and practical?
   - Are the expected outcomes clearly measurable?

4. **Scientific Innovation and Practical Value (0-10 points)**:
   - Does the research query have academic merit?
   - Do the results have real-world application potential?

Return in JSON format (JSON only):
{{
  "total_score": <integer from 0-100>,
  "dimension_scores": {{
    "academic_rigor": <0-25>,
    "comprehensive_tool_utilization": <0-35>,
    "feasibility": <0-30>,
    "scientific_innovation_and_practical_value": <0-10>
  }},
  "detailed_evaluation": "2-3 sentences of detailed analysis",
  "improvement_suggestions": "Specific recommendations for improvement"
}}"""

REVISE_SYSTEM = """You are an experienced AI research assistant and research task optimization expert. Your responsibility is to receive an existing research query with its proposal, modification suggestions, and the original paper context, then output an improved, more compliant new proposal.
🔴 [CORE REQUIREMENT] Your optimized proposal must still adhere to the principle of "using at least 3 different tools" and ensure all modifications closely align with both the paper excerpt and the improvement suggestions."""

REVISE_USER = """
[AVAILABLE TOOLS]
{tools}

[ORIGINAL RESEARCH PAPER EXCERPT]
{text}

[PREVIOUS RESEARCH TASK PROPOSAL]
{query}

[RECEIVED IMPROVEMENT SUGGESTIONS]
{critic}

Based on the "improvement suggestions" above and staying closely aligned with the "original research paper excerpt," optimize and refine the "previous research task proposal."
🔴 [MANDATORY] Ensure the new proposal still clearly specifies how to employ exactly 3 different tools.

Return in strict JSON format (JSON only, no other text):
{{
  "new_research_query": "Detailed, clear description of the research query and objectives",
  "required_tools": ["Tool A", "Tool B", "Tool C"],
  "research_scope_and_steps": "Phase-by-phase explanation of research scope, methodology, and specific logic of tool utilization",
  "evaluation_metrics": ["Metric 1", "Metric 2"]
}}"""

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
{{
   "goal_paragraph_indexes": [2],
   "recipe_paragraph_indexes": [6, 7]
}}
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