STEP_1 = """You are an expert scientific data engineer. You are given a paragraph from a scientific paper. 

Task: Determine whether the paragraph contains a concrete, paper-specific scientific claim that could later be examined, questioned, or reasoned about.

A valid claim must:
- Be specific to this paper (not general background knowledge).
- Reflect an observation, comparison, dependency, or constraint.
- Not be purely methodological description.

Answer in JSON:
{
  "extractable": true | false,
  "reason": "brief explanation"
}
"""

STEP_1_USER = """[Paper title]
{title}

[Section name]
{name}

[Paragraph]
{text}
"""

STEP_2 = """You are an expert scientific data engineer. You are extracting structured scientific knowledge from a research paper.

Task: Given the paragraph below, extract ONE primary scientific knowledge unit.

A valid knowledge unit must satisfy:
- The claim is directly supported by the given paragraph.
- The claim reflects a paper-specific scientific result, not general background knowledge.
- The claim would NOT be reliably answerable without access to this paper.
- Do NOT generalize beyond what is stated.
- Do NOT invent numerical values or refer to figures unless explicitly mentioned.

In addition, you must explicitly judge whether the claim is paper-grounded. A paper-grounded claim is one that:
- Depends on the specific experiment, analysis, or evidence in this paper
- Cannot be verified or confidently stated without this paper

Return STRICT JSON in the following format:

{
  "claim": "...",
  "claim_type": "observation | comparison | dependency | negative_result | constraint",
  "method_signature": "...",
  "experimental_or_analysis_context": {
    "domain": "...",
    "conditions": "..."
  },
  "evidence": {
    "evidence_type": "measurement | simulation | analysis | characterization",
    "text_anchor": ["exact sentence(s) from the paragraph", ...]
  },
  "paper_grounded": true | false
}
"""

STEP_2_USER = """[Paper title]
{title}

[Section name]
{name}

[Paragraph]
{text}
"""

STEP_2_SCHEMA = {
  "type": "object",
  "required": ["claim", "claim_type", "method_signature", "experimental_or_analysis_context", "evidence", "paper_grounded"],
  "properties": {
    "claim": {"type": "string", "minLength": 1},
    "claim_type": {
      "type": "string",
      "enum": ["observation", "comparison", "dependency", "negative_result", "constraint"]
    },
    "method_signature": {"type": "string"},
    "experimental_or_analysis_context": {
      "type": "object",
      "required": ["domain", "conditions"],
      "properties": {"domain": {"type": "string"}, "conditions": {"type": "string"}}
    },
    "evidence": {
      "type": "object",
      "required": ["evidence_type", "text_anchor"],
      "properties": {
        "evidence_type": {
          "type": "string",
          "enum": ["measurement", "simulation", "analysis", "characterization"]
        },
        "text_anchor": {"type": "array", "items": {"type": "string"}}
      }
    },
    "paper_grounded": {"type": "boolean"}
  },
  "additionalProperties": False
}

STEP_12 = """You are an expert scientific data engineer. You are extracting structured, paper-specific scientific knowledge from a research paper.

Given the paragraph below, decide whether it contains a VALID extractable scientific knowledge unit. If YES, extract exactly ONE knowledge unit. If NO, return an empty object.

A paragraph is VALID for extraction only if it satisfies ALL of the following:
- It states a concrete scientific result, finding, constraint, or dependency.
- The claim is directly supported by this paragraph alone.
- The claim is NOT general background knowledge or a definition.
- The claim would NOT be reliably answerable without access to this paper.
- The claim does NOT require wet-lab execution to be verified.
- Do NOT invent values, extrapolate, or generalize beyond the paragraph.

If the paragraph is NOT valid, return:
```json
{}
```

If the paragraph IS valid, return STRICT JSON in the format below.

You must also explicitly judge whether the claim is paper-grounded.

A paper-grounded claim:
- Depends on specific experiments, analyses, or evidence in this paper
- Cannot be confidently stated or verified without this paper

Return ONLY one of the two options: null OR a JSON object.

JSON format:
```json
{
  "claim": "...",
  "claim_type": "observation | comparison | dependency | negative_result | constraint",
  "method_signature": "...",
  "experimental_or_analysis_context": {
    "domain": "...",
    "conditions": "..."
  },
  "evidence": {
    "evidence_type": "measurement | simulation | analysis | characterization",
    "text_anchor": ["exact sentence(s) from the paragraph", ...]
  },
  "paper_grounded": true | false
}
```
"""

STEP_3 = """Given the claim and the textual anchors, decide whether the claim is fully and strictly supported by the anchors alone.

Answer in JSON:
{
  "fully_supported": true | false,
  "unsupported_parts": ["..."]
}
"""

STEP_3_USER = """[claim]
{claim}

[textual anchors]
{text}"""
