import re
import json
import tqdm
import requests
from concurrent.futures import ThreadPoolExecutor as TPE
from typing import List, Dict, Any
import multiprocessing as mp

# =========================
# Load LLM config
# =========================
with open("config.json", "r", encoding="utf-8") as f:
    llm_cfg = json.load(f)

print(llm_cfg)

# =========================
# Prompt
# =========================
SYSTEM_PROMPT = """You are a senior scientific benchmark curator.

You will be given a list of queries.
For EACH query, determine whether it has genuine scientific research value
and is suitable for evaluating a scientific AI agent.

Keep a query if it involves:
- scientific reasoning, hypotheses, mechanisms, experiments, or data analysis
- biology, medicine, chemistry, physics, AI, or interdisciplinary research
- non-trivial research objectives

Discard queries that are:
- general knowledge
- simple factual lookup
- software usage or environment setup
- lacking research intent
"""

USER_PROMPT_TEMPLATE = """
Input queries follow this example:
[
  {{ "query_id": 0, "query": "query 1" }},
  {{ "query_id": 1, "query": "query 2" }},
  ...
]

Output format: Return ONLY a JSON array.
Each element corresponds to one query, in the same order.

Output format example:
[
  {{ "query_id": 0, "keep": true }},
  {{ "query_id": 1, "keep": false }},
  ...
]

Queries:
{queries}
"""

def extract_json(text: str) -> dict:
    """从文本中提取 JSON 对象"""
    if not text:
        return {}
    
    try:
        return json.loads(text)
    except Exception:
        pass
    
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return {}
    
    try:
        candidate = text[start:end+1].replace("'", '"')
        candidate = re.sub(r",\s*([}\]])", r"\1", candidate)
        return json.loads(candidate)
    except Exception:
        return {}

# =========================
# Batch Judge
# =========================
def batch_is_scientific(queries: List[Dict[str, Any]]) -> List[bool]:
    input_queries = ','.join(f'  {{ \"query_id\": {i}, \"query\": {q["query"]} }}' for i, q in enumerate(queries))
    retry = 5
    while retry >= 0:        
        try:
            headers = {"Content-type": "application/json", "Authorization": f"Bearer {llm_cfg['api_key']}"}
            response = requests.post(f"{llm_cfg['base_url']}/chat/completions", headers=headers, json={
                "model": llm_cfg['model'],
                "temperature": 0,
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {
                        "role": "user",
                        "content": USER_PROMPT_TEMPLATE.format(queries=f"[\n{input_queries}\n]")
                    }
                ]
            })
            result = extract_json(response.json()['choices'][0]['message']['content'].strip())
            if len(result) != len(queries):
                raise ValueError("Result length mismatch")
            keep = []
            for item in result:
                idx = int(item['query_id'])
                if bool(item.get("keep", False)):
                    keep.append(queries[idx])
            return keep
        except Exception as e:
            print(f"⚠️ Batch parse failed because of {e}. Retry: {retry}")
            retry -= 1
    return []


# =========================
# Load input file
# =========================
def load_local(fn):
    with open(fn, "r+", encoding="utf-8") as f:
        d = [json.loads(line.strip()) for line in f if line.strip()]
    return d


def print_json(d, fn):
    with open(fn, "a+", encoding="utf-8") as f:
        for x in d:
            f.write(json.dumps(x, ensure_ascii=False) + "\n")


# =========================
# Main filtering logic
# =========================
def filter_queries(
    input_path: str,
    output_path: str,
    batch_size: int = 10,
):
    queries = load_local(input_path)

    total = len(queries)
    print(f"Loaded {total} queries.")

    tasks = [queries[start:start + batch_size] for start in range(0, total, batch_size)]

    count = 0
    with TPE(max_workers=10) as pool:
        for kept in tqdm.tqdm(pool.map(batch_is_scientific, tasks), total=len(tasks)):
            print_json(kept, output_path)
            count += len(kept)

    
    print(f"Done. Kept {count} / {total} queries.")


# =========================
# Entry
# =========================
if __name__ == "__main__":
    filter_queries(
        input_path="化学-500条.jsonl",
        output_path="化学筛选.jsonl",
        batch_size=10
    )
