from prompts import *
from .base import AsyncLLMClient


class BenchmarkTest(AsyncLLMClient):
    SYSTEM = ""
    
    async def _organize_inputs(self, inputs):
        return [{"role": "system", "content": self.SYSTEM}, {"role": "user", "content": inputs}], {}


class HLETest(BenchmarkTest):
    async def _availability(self, response: str, context: dict):
        response = response.split("\n")
        explanation, answer, confidence = [], [], []
        field = None
        for r in response:
            if r.startswith("Explanation: "):
                field = "explanation"
                r = r[len("Explanation: "):]
            if field == 'explanation': explanation.append(r.strip())
            if r.startswith("Answer: "):
                field = "answer"
                r = r[len("Answer: "):]
            if field == 'answer': answer.append(r.strip())
            if r.startswith("Confidence: "):
                field = "confidence"
                r = r[len("Confidence: "):]
            if field == 'confidence': confidence.append(r.strip())
        assert explanation and answer
        return {"id": context['id'], 'q': context['question'], "explanation": "\n".join(explanation), 
                "answer": "\n".join(answer), "confidence": "\n".join(confidence)}
    
    async def _organize_inputs(self, inputs):
        return [{"role": "system", "content": HLE}, {"role": "user", "content": inputs['question']}], inputs