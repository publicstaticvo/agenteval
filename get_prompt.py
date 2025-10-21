def prompt_for_query(x):
    prompt = f"""You are a professional scientific AI agent researcher, currently collaborating with us at DeepMind. Due to research needs, you are now required to transform and generate a batch of high-quality, expert-level scientific research questions for chemistry. To ensure the scientific nature and challenge of the generation task, the criteria for "high-quality, expert-level questions" are defined as follows:

Goal: To construct high-quality, expert-level questions that simulate real scientific research tasks.

Requirements:  
1. They must have a certain level of complexity and difficulty, at the level of professional chemistry researchers.
2. They need to involve at least two or more professional chemistry tool calls.
3. They should be as realistic as possible.

Example:  
Original question: "What are the technical limitations of ECHs and conductive polymers for biomedical applications?"  
Evaluation: This is a typical low-quality, fact-retrieval query. Its answer requires the model to perform simple searches.  
New question: "Let's conceptualize a new conductive hydrogel system for cardiac repair. Obviously, the old routes like graphene oxide or polyaniline have too many issues. Considering new materials from the past two years, such as MXenes or conductive MOFs, which one do you think, when combined with a matrix like GelMA, has the most potential to simultaneously achieve myocardial-level mechanical properties (approximately how many kPa?) and electrical conductivity? The key is, how to design this system to decouple or synergistically regulate these two properties."  
Involves: literature retrieval tools, database tools, and finally requires model reasoning.  

The following is the original question that needs to be transformed:  

[Start of the original question]
{x['q']}  
[End of the original question]

Please transform the above question into new questions from 2-3 different perspectives. Please output the transformed questions in JSON format. For example:  

```json
{{  
  "transformed_questions": [  
    {{  
      "perspective": "{{perspective 1}}",  
      "question": "{{question 1}}"  
    }},  
    {{  
      "perspective": "{{perspective 2}}",  
      "question": "{{question 2}}"  
    }}  
  ]  
}}
```

"""

    return [{'role': 'user', 'content': prompt}]