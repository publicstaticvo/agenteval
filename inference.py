import json
import os
import glob
import time
import tqdm
import argparse
import regex
import random
import requests
import multiprocessing
from requests.exceptions import ConnectionError, Timeout, RequestException
from get_prompt import *

# load_api_key
with open("../api_key.json") as f: json_key = json.load(f)
key = {}
for k in ['cstcloud', 'deepseek']:
    for m in json_key[k]['models']:
        key[m] = {"base_url": json_key[k]['domain'], "api_key": json_key[k]['key']}


def get_message(line, func):
    if func: return func(line)
    messages = []
    if 'user_prompt' in line:
        messages.append({"role": 'user', "content": line['user_prompt']})
    elif 'prompt' in line:
        messages.append({"role": 'user', "content": line['prompt']})
    if 'system_prompt' in line:
        messages = [{"role": 'system', "content": line['system_prompt']}] + messages
    return messages


def call_by_request(messages, model, base_url, api_key, args, retry=5):
    while retry > 0:
        try:
            sampling_params = {
                "model": model,
                "messages": messages,
                "temperature": 0.6,
                "top_p": 0.95, "top_k": 20,
                "max_tokens": args.max_tokens,
                "stream": args.stream
            }
            headers = {'Content-Type': 'application/json', 'Authorization': f'Bearer {api_key}'}
            url = f"{base_url}/v1/chat/completions"
            response = requests.post(url, headers=headers, data=json.dumps(sampling_params), timeout=600)
            response.raise_for_status()
            message = json.loads(response.text)['choices'][0]['message']
            text = message['content']     
            if "reasoning_content" in message: 
                think = message['reasoning_content']
            elif "</think>" in text:
                think = text[:text.index("</think>")]
                text = text[text.index("</think>") + 8:]
            else:
                think = ""
            return text
        except Exception as e:
            retry -= 1
            print(f"Error: {e}, Retry: {retry}")
            time.sleep(10)    


def call(line, args, output_file="", retry=5):
    # 需要：每个输入样本line的格式为{"system_prompt": ..., "user_prompt": ...}
    # 确保：将一条{"system_prompt": ..., "user_prompt": ..., "greedy": "输出结果"}的数据以"a+"的方式写入输出文件。
    # 为了节省输入文件大小，可以将组装system_prompt和user_prompt的步骤放在此处。 
    messages = prompt_for_query(line) 
    if "request_models" in line:
        models = line['request_models']
        assert all(m in key for m in models), (models, list(key.keys()))
        samples = {m: [] for m in models}
        for m in models:
            info = key[m]
            base_url, api_key = info['base_url'], info['api_key']
            if args.base_url: base_url = args.base_url
            if args.api_key and args.api_key != "EMPTY": api_key = args.api_key
            for _ in range(args.n_samples):
                text = call_by_request(messages, m, base_url, api_key, args, retry)
                if text: samples[m].append(text)
        if args.n_samples == 1:
            samples = {m: (v[0] if v else "") for m, v in samples.items()}
    else:
        assert args.model and args.base_url and args.api_key and args.api_key != 'EMPTY'
        samples = []
        for _ in range(args.n_samples):            
            text = call_by_request(messages, args.model, args.base_url, args.api_key, args, retry)
            if text: samples.append(text)
    if output_file:
        if args.n_samples == 1 and "request_models" not in line: 
            if samples: line["greedy"] = samples[0]
            else: return []
        else: 
            line["samples"] = samples
            if "request_models" in line: del line['request_models']
        with open(output_file, 'a+', encoding="utf-8") as fp:
            fp.write(json.dumps(line, ensure_ascii=False) + '\n')
    return samples
    


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--api_key', type=str, default="EMPTY")
    parser.add_argument('--base_url', type=str, default="")
    parser.add_argument('--inputs', type=str, required=True)
    parser.add_argument('--max_tokens', type=int, default=1024)
    parser.add_argument('--model', type=str, default="gpt-oss-120b")
    parser.add_argument('--n_samples', type=int, default=1)
    parser.add_argument('--n_workers', type=int, default=60)
    parser.add_argument('--output', type=str, default="output.jsonl")
    parser.add_argument('--stream', action='store_true')
    args = parser.parse_args()
    t = time.time()
    print(f"使用并行进程数: {args.n_workers}")
    with multiprocessing.Pool(processes=args.n_workers) as pool:
        pending_results = []
        with open(args.inputs, encoding="utf-8") as f_in:
            for line in f_in:
                x = json.loads(line.strip())
                if not x: continue
                pending_results.append(pool.apply_async(call, (x, args, args.output)))
        print("finish pending results")
        for async_result in tqdm.tqdm(pending_results): async_result.get()
    print(f"Time: {time.time() - t:.4f}")
