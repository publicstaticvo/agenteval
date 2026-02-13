import json, jsonschema
import asyncio
from prompts import *
from utils import extract_json
from .base import AsyncLLMClient

SAMPLE_PARAMS = {'temperature': 0.8, "max_tokens": 8192, "top_p": 0.95}


class Generate(AsyncLLMClient):

    def _availability(self, response: str, context: dict):
        text = extract_json(response)
        assert text, response
        jsonschema.validate(text, GENERATE_SCHEMA)
        questions = []
        # 预过滤
        STOP_WORDS = ['fig.', 'tbl.', 'see fig', 'shown in fig', 'the proposed',
                      'see section', 'this section', 'sec.', 'appendix', 'eq.', 'the paper', 'this paper']
        for x in text['questions']:
            if any(y in x['question'].lower() for y in STOP_WORDS): continue
            questions.append(x)
        assert len(questions) > 0, questions
        return questions
    
    def _organize_inputs(self, inputs):
        inputs = json.dumps(inputs, indent=2)
        return [{'role': 'system', 'content': GENERATE}, {'role': 'user', 'content': inputs}], {}


class Rewrite(AsyncLLMClient):

    PROMPT = REVISE
    SCHEMA = REVISE_SCHEMA
    
    def _organize_inputs(self, inputs):
        inputs = json.dumps(inputs, indent=2)
        return [{'role': 'system', 'content': self.PROMPT}, {'role': 'user', 'content': inputs}], {}
    

async def generate(content: dict):
    model = Generate(config.generate_model, SAMPLE_PARAMS, 1800)
    try:
        generated = await model.call(inputs=content)
        return generated
    except Exception as e:
        print(f"GenerateNode {e}")
    

async def rewrite(generated: list[dict]):
    tasks = [asyncio.create_task(Rewrite(config.generate_model, SAMPLE_PARAMS).call(inputs=g)) for g in generated]
    refine = []
    for task in asyncio.as_completed(tasks):
        try:
            result = await task
            if result: refine.append(result)
        except Exception as e:
            print(f"RewriteNode {e}")
    return refine
