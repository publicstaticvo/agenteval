import jsonschema
from prompts import *
from .base import AsyncLLMClient
from utils import extract_json


class BenchmarkTest(AsyncLLMClient):
    SYSTEM = ""
    
    def _organize_inputs(self, inputs):
        return [{"role": "system", "content": self.SYSTEM}, {"role": "user", "content": inputs}], {}


class HLETest(BenchmarkTest):
    def _availability(self, response: str, context: dict):
        text = extract_json(response)
        jsonschema.validate(text, HLE_SCHEMA)
        return {"id": context['id'], 'q': context['question'], **text}
        # return {"answer": response, 'id': context['id'], 'q': context['question']}
    
    def _organize_inputs(self, inputs):
        return [{"role": "system", "content": HLE}, {"role": "user", "content": inputs['question']}], inputs
        # return [{"role": "user", "content": inputs['question']}], inputs