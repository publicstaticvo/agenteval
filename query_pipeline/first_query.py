import os
import re
import json
import time
import tqdm
from openai import OpenAI
from dotenv import load_dotenv
from functools import partial
from concurrent.futures import ThreadPoolExecutor as TPE

from config import Config
from prompts import FIRST_QUERY
# import logging
# logging.basicConfig(filename="chem.log")

load_dotenv()

# -----------------------------------------------
# 初始化 DeepSeek API 客户端
# -----------------------------------------------
with open("../../api_key.json") as f: json_key = json.load(f)
key = {}
for k in ['cstcloud', 'deepseek']:
    for m in json_key[k]['models']:
        key[m] = {"base_url": json_key[k]['domain'], "api_key": json_key[k]['key']}

config = Config.from_yaml("chemistry.yaml")
print(config)
model = config.model
print(key[model])
client = OpenAI(api_key=key[model]['api_key'], base_url=f"{key[model]['base_url']}/v1")


# -----------------------------------------------
# 读取工具定义
# -----------------------------------------------
def load_tools_from_json(tools_file: str) -> dict:
    """
    从 JSON 文件中读取工具定义。
    支持两种格式：
    1. 顶层为 {"tools": [ ... ]}
    2. 顶层直接为 [ ... ]
    """
    if not os.path.exists(tools_file):
        raise FileNotFoundError(f"❌ 工具文件不存在: {tools_file}")
    
    with open(tools_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    # ✅ 自动识别文件结构
    if isinstance(data, dict) and "tools" in data:
        tools = data["tools"]
    elif isinstance(data, list):
        tools = data
    else:
        raise ValueError("工具文件格式错误：应为 {'tools': [...]} 或 [...].")

    print(f"✅ 已加载 {len(tools)} 个工具")
    return {"tools": tools}


def format_tools_description(tools: list) -> str:
    """
    将工具列表格式化为描述文本。
    
    Args:
        tools: 工具列表
    
    Returns:
        str: 格式化的工具描述
    """
    description = "可用的工具列表：\n"
    for tool in tools:
        name = tool.get("name", "Unknown")
        desc = tool.get("description", "No description")
        description += f"\n- 【{name}】: {desc}"
        
        # 如果有参数，也加入描述
        if "parameters" in tool:
            params = tool["parameters"]
            if isinstance(params, dict) and "properties" in params:
                description += "\n  参数: " + ", ".join(params["properties"].keys())
    
    return description


# -----------------------------------------------
# 生成针对工具的 Query
# -----------------------------------------------
def generate_queries_for_tools(seed_query: str, tools: list, n_queries: int = 5, retry: int = 5) -> list:
    """
    根据工具定义生成针对性的测试 query。
    
    Args:
        tools: 工具列表
        domain: 应用领域（如果为 None，从工具名称推断）
        n_queries: 生成的问题数量
    
    Returns:
        List[str]: 生成的查询列表
    """
    tools_desc = format_tools_description(tools)
    user = FIRST_QUERY.format(seed=seed_query, tools=tools_desc, n_queries=n_queries)
    
    while retry > 0:
        try:
            response = client.chat.completions.create(
                model=config.model,
                messages=[
                    {
                        "role": "system",
                        "content": "你是一个专业的测试数据生成助手，能够根据可用工具生成真实有效的用户查询。"
                    },
                    {
                        "role": "user",
                        "content": user
                    }
                ],
                temperature=1,
                max_tokens=2500
            )
            
            content = response.choices[0].message.content.strip()
            queries = _parse_response(content)
            
            if not queries:
                raise ValueError("生成的 query 为空")            
            return queries
        
        except Exception as e:
            retry -= 1
            print(f"❌ 调用 API 失败: {e}，重试：{retry}")
            time.sleep(10)
    return []


def _parse_response(content: str) -> list:
    """
    从 API 响应中解析 JSON 数组。
    
    Args:
        content: API 返回的内容
    
    Returns:
        List[str]: 解析后的查询列表
    """
    content = content.strip()
    
    # 尝试直接解析为 JSON
    try:
        queries = json.loads(content)
        if isinstance(queries, list) and all(isinstance(q, str) for q in queries):
            return [q.strip() for q in queries if q.strip()]
    except json.JSONDecodeError:
        pass
    
    # 尝试从 Markdown 代码块中提取 JSON
    try:
        match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', content)
        if match:
            json_str = match.group(1)
            queries = json.loads(json_str)
            if isinstance(queries, list) and all(isinstance(q, str) for q in queries):
                return [q.strip() for q in queries if q.strip()]
    except json.JSONDecodeError:
        pass
    
    # 降级方案：按行分割
    lines = content.split("\n")
    queries = []
    for line in lines:
        cleaned = re.sub(r'^[\d]+[.、\-)\s]*|^[•\-\*]\s*', '', line.strip())
        if cleaned and len(cleaned) > 10:
            queries.append(cleaned)
    
    return queries


# -----------------------------------------------
# 保存 Query
# -----------------------------------------------
def save_queries_to_json(queries: list, filename: str, tools_file: str = None) -> str:
    """
    将生成的 query 保存到 JSON 文件。
    
    Args:
        queries: 查询列表
        domain: 应用领域
        tools_file: 工具文件路径（用于参考）
    
    Returns:
        str: 保存的文件路径
    """
    
    data = {
        "count": len(queries),
        "tools_file": tools_file,
        "queries": queries
    }
    
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    print(f"✅ 已保存 {len(queries)} 条 query 到 {filename}")
    return filename


def display_queries(queries: list) -> None:
    """展示生成的 query。"""
    print("\n" + "="*70)
    print("📋 生成的查询列表：")
    print("="*70)
    for i, query in enumerate(queries, 1):
        print(f"\n[{i}] {query}")
    print("\n" + "="*70)


# -----------------------------------------------
# 主执行入口
# -----------------------------------------------
if __name__ == "__main__":    
    try:
        # 获取工具文件路径加载工具
        tools = load_tools_from_json(config.tool_file).get("tools", [])
        if not tools:
            print("❌ 未找到有效的工具定义")
            exit(1)
        
        # 加载种子query
        with open(config.input_file, encoding='utf-8') as f: seed_queries = json.load(f)['queries']
        
        # 生成 query
        print(f"并行为{len(seed_queries)}个种子query生成工具query每个各{config.n_queries}个")
        generate_funcion = partial(generate_queries_for_tools, tools=tools, n_queries=config.n_queries)
        queries = []
        for x in seed_queries:
            generate_funcion(seed_query=x)
        # with TPE(max_workers=20) as pool:
        #     for result in tqdm.tqdm(pool.map(generate_funcion, seed_queries), total=len(seed_queries)):
        #         queries.extend(result)
        # print(f"✅ 成功生成 {len(queries)} 条 query")
        # display_queries(queries[:5])
        # save_queries_to_json(queries, config.first_output, config.tool_file)
        
    except KeyboardInterrupt:
        print("\n⚠️  用户中断")
    except Exception as e:
        print(f"\n❌ 发生错误: {e}")