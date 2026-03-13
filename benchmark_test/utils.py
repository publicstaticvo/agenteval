import re
import os
import sys
import json
import asyncio
import unidecode

URL_DOMAIN = "https://openalex.org/"
_is_shutting_down = False


def load_local(fn):
    with open(fn, "r+", encoding="utf-8") as f:
        d = [json.loads(line.strip()) for line in f if line.strip()]
    return d


def print_json(d, fn, mode='w+'):
    with open(fn, mode, encoding="utf-8") as f:
        for x in d:
            f.write(json.dumps(x, ensure_ascii=False) + "\n")


def robust_backslash(text: str) -> str:
    result = []
    i = 0
    in_latex = False
    
    while i < len(text):
        char = text[i]
        
        # 处理 $ 符号
        if char == '$':
            if i == 0 or text[i - 1] != '$': in_latex = not in_latex
            result.append(char)
            i += 1
        # 处理反斜杠
        elif char == '\\' and i + 1 < len(text):
            next_char = text[i + 1]            
            if in_latex:
                # 在 LaTeX 块内
                # 判断是否是真正的转义序列：n, t, r, \\ 
                # 但需要检查后续：如果 \n 后面跟着字母，则它是 \nabla 等命令的一部分
                if next_char in ('n', 't', 'r'):
                    # 检查再后面的字符
                    if i + 2 < len(text) and text[i + 2].isalpha():
                        # 如 \nabla, \tilde, \rho - 是 LaTeX 命令，需要双倍
                        result.append('\\\\')
                        result.append(next_char)
                        i += 2
                    else:
                        # 真正的转义序列（\n 后面是非字母），保留
                        result.append('\\')
                        result.append(next_char)
                        i += 2
                elif next_char == '\\':
                    # \\，保留
                    result.append('\\')
                    result.append(next_char)
                    i += 2
                else:
                    # 其他字符后的反斜杠（如 \alpha, \beta, \frac），双倍处理
                    result.append('\\\\')
                    result.append(next_char)
                    i += 2
            elif next_char in ['(', ')', '[', ']']:
                # \( \) \[ \]
                in_latex = not in_latex
                if i >= 1 and text[i - 1] != "\\": result.append('\\\\')
                else: result.append('\\')
                i += 1
            else:
                # 在 LaTeX 块外，保持原样
                result.append('\\')
                i += 1
        else:
            result.append(char)
            i += 1
    
    return ''.join(result)


def extract_json(text: str) -> dict:
    """从文本中提取 JSON 对象"""
    if not text: return {}
    text = robust_backslash(text)
    text = re.sub(r"\s+", " ", text)
    
    try:
        return json.loads(text)
    except Exception as e:
        print(e)
        pass
    
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return {}
    
    try:
        candidate = text[start:end+1]  # .replace("'", '"')
        candidate = re.sub(r",\s*([}\]])", r"\1", candidate)
        return json.loads(candidate)
    except Exception:
        return {}
    

def set_shutdown():
    global _is_shutting_down
    _is_shutting_down = True


def get_shutdown():
    return _is_shutting_down


def handle_exception(loop, context: dict):
    msg = context.get("exception", context["message"])
    print(f"捕获到异常: {msg}")


def signal_handler(sig, frame):
    """同步信号处理器 - Windows 兼容"""
    print(f"\n捕获到信号 {sig}")
    # 在 Windows 上，我们不能直接调用异步函数，需要设置事件或使用 create_task
    try:
        loop = asyncio.get_running_loop()
        loop.create_task(shutdown())
        # 停止事件循环
        loop.stop()
    except RuntimeError:
        # 如果没有运行中的循环，直接退出
        sys.exit(0)


async def shutdown():
    """清理所有挂起的任务"""
    loop = asyncio.get_running_loop()
    tasks = [t for t in asyncio.all_tasks(loop) if t is not asyncio.current_task()]    
    print(f"正在取消 {len(tasks)} 个任务...")
    for task in tasks: task.cancel()    
    if tasks: await asyncio.gather(*tasks, return_exceptions=True)


if __name__ == "__main__":
    string = """{
    "explanation": "For a rotating liquid surface the free‑surface shape is a paraboloid given by \\(z(r)=\\frac{\\omega^2 r^2}{2g}\\).  A paraboloid of focal length \\(f\\) satisfies \\(z(r)=\\frac{r^2}{4f}\\).  Equating the two forms gives \\(\\frac{1}{4f}=\\frac{\\omega^2}{2g}\\) so \\(f=\\frac{g}{2\\omega^2}\\).  The angular speed is driven by a constant power source \\(P\\).  Power equals the rate of change of kinetic energy of the rotating fluid: \\(P=\\frac{d}{dt}\\left(\\frac12 I\\omega^2\\right)=I\\omega\\dot\\omega\\).  With constant \\(P\\) and constant moment of inertia \\(I\\) (solid‑body rotation of the liquid), \\(\\omega\\dot\\omega=P/I\\) ⇒ \\(\\frac{d}{dt}(\\omega^2)=2P/I\\).  Integrating from rest, \\(\\omega^2=(2P/I) t\\), i.e. \\(\\omega^2\\propto t\\).  Substituting into the focal‑length expression gives \\(f\\propto 1/\\omega^2\\propto 1/t\\).  Hence \\(f\\propto t^{n}\\) with \\(n=-1\\).",
    "answer": -1,
    "confidence": "99%"
}"""
    print(extract_json(string))
