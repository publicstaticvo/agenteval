import re
import os
import json
import unidecode
from paper_elements import Paragraph

URL_DOMAIN = "https://openalex.org/"


def index_to_abstract(indexes: dict | None):
    if not indexes: return None
    abstract_length = max(v[-1] for v in indexes.values())
    abstract = ["<mask>" for _ in range(abstract_length + 1)]
    for k, v in indexes.items():
        for i in v:
            abstract[i] = k
    return " ".join(abstract)


def valid_check(query: str, target: str) -> bool:
    def normalize(text: str) -> str:
        text = unidecode.unidecode(text)
        text = re.sub(r"[^0-9a-zA-Z\s]", "", text)
        return text.lower()
    
    return normalize(query) == normalize(target)


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


def load_tools(tools_file: str) -> list:
    """加载工具描述文件"""
    if not tools_file or not os.path.exists(tools_file):
        print(f"⚠️  工具文件不存在: {tools_file}")
        return []
    
    try:
        with open(tools_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        tools = data if isinstance(data, list) else data.get("tools", [])
        print(f"✅ 加载了 {len(tools)} 个工具")
        return tools
    except Exception as e:
        print(f"❌ 加载工具文件失败: {e}")
        return []


def format_tools_context(tools: list[dict[str, str]]) -> str:
    """格式化工具信息供提示词使用"""
    if not tools:
        return "（未提供工具列表）"
    
    lines = ["可用工具清单："]
    for tool in tools:
        name = tool.get("name", tool.get("tool_name", "unknown"))
        desc = tool.get("description", tool.get("tool_description", "no description"))
        lines.append(f"  - {name}: {desc}")
    
    return "\n".join(lines)


def extract_queries(input_data: str) -> list:
    """提取 queries 列表"""
    input_data = input_data.strip()
    
    if input_data.endswith('.json') and os.path.exists(input_data):
        with open(input_data, 'r', encoding='utf-8') as f:
            input_data = f.read()
    
    try:
        parsed = json.loads(input_data)
        if isinstance(parsed, list):
            return [q.strip() for q in parsed if isinstance(q, str) and q.strip()]
        if isinstance(parsed, dict):
            queries = parsed.get("queries") or parsed.get("query", [])
            if isinstance(queries, list):
                return [q.strip() for q in queries if isinstance(q, str) and q.strip()]
            return [queries.strip()] if isinstance(queries, str) else []
    except json.JSONDecodeError:
        pass
    
    return [input_data] if input_data else []


# ==================== SearchNode ====================
def get_metadata(paper: dict):
    # The following information to get:
    return {
        "id": paper['id'].replace(URL_DOMAIN, ""),
        "title": paper['display_name'],
        "authors": paper['authorship'],
        "locations": [x['source'] for x in paper['locations']],
        "cited_by_count": paper['cited_by_count'],
        "counts_by_year": paper['counts_by_year'],
        "publication_date": paper['publication_date'],
    }


def yield_location(x):
    urls = set()
    y = x["best_oa_location"]
    if y and y['pdf_url']: 
        urls.add(y['pdf_url'])
        yield y['pdf_url']
    for y in x['locations']:
        if y['pdf_url'] and y['pdf_url'] not in urls: 
            urls.add(y['pdf_url'])
            yield y['pdf_url']


def skeleton_to_list(paper: list[str | Paragraph], mode: str = "first") -> tuple[str, list[str]]:
    repr_str, paragraphs = [], []
    p_count = 0
    for p in paper:
        if isinstance(p, str):  # 章节标题
            repr_str.append(p)
        else:
            p_count += 1
            p.text = re.sub(r"\s+", " ", p.text)
            sentence = re.split(r'(?<=[.!?])\s+', p.text, 1)[0] if mode == "first" else p.text
            repr_str.append(f"Paragraph {p_count}: {sentence} ...\n")
            paragraphs.append(p.text)
    context = '\n'.join(repr_str)
    return context, paragraphs


def skeleton_to_dict(paper: list[str | Paragraph]) -> str:
    repr_dict = []
    for p in paper:
        if isinstance(p, str):  # 章节标题
            repr_dict.append({"section_name": p, "paragraphs": []})
        else:
            repr_dict[-1]['paragraphs'].append(re.sub(r"\s+", " ", p.text))
    return json.dumps(repr_dict, ensure_ascii=False, indent=2)


def save_result(result: dict, file_path: str) -> None:
    """实时保存单个结果"""
    try:        
        with open(file_path, 'a+', encoding='utf-8') as f:
            f.write(json.dumps(result, ensure_ascii=False) + "\n")
    except KeyboardInterrupt:
        raise
    except Exception:
        pass
