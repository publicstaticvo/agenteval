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


def prompt_for_scoring(x):
    prompt = f"""You are a professional scientific AI agent researcher, currently collaborating with us at DeepMind. We have collected a set of AI-generated chemistry questions. Your task is to evaluate a given research question based on the following criteria and output the results in JSON format after careful reasoning.

**Criteria for Evaluation:**
1. **Correctness**: Assess whether the question is correct, feasible and solvable, with clear meaning free from ambiguity, scientific inaccuracies, or self-contradictions. Score on a scale of 1 to 5, where 1 indicates highly incorrect or unclear, and 5 indicates perfectly correct and clear.
2. **Complexity**: Evaluate whether the question is at the level of professional scientific research in chemistry and requires the use of at least two different chemistry research tools (e.g., computational modeling, experimental instruments, databases) to solve. Score on a scale of 1 to 5, where 1 indicates low complexity (simple or tool-free) and 5 indicates high complexity (requiring multiple advanced tools).
3. **Authenticity and Value**: Determine whether the question reflects a real-world research scenario and has value for further investigation or experimentation. Score on a scale of 1 to 5, where 1 indicates unrealistic or low value, and 5 indicates highly authentic and valuable.

**Additional Classification:**
- Classify the question type as either "fixed_answer" (if it has a definitive, known answer) or "open_ended" (if it requires exploration, interpretation, or lacks a single correct answer).

**Output Format:**
After your analysis, provide the evaluation in the following JSON structure:
```json
{{
  "scores": {{
    "correctness": [score between 1 and 5],
    "complexity": [score between 1 and 5],
    "authenticity_and_value": [score between 1 and 5]
  }},
  "classification": ["fixed_answer" or "open_ended"]
}}
```

**Instructions:**
- Think step by step through each criterion before generating the JSON output.
- Consider the question in the context of current scientific knowledge and practices.

For the question: {x['q']}"""
    return [{'role': 'user', 'content': prompt}]


def prompt_for_topics(x):
    prompt = f"""You are a professional scientific AI agent researcher, currently collaborating with us at DeepMind. We are training a model that scores relevance between papers and review topics. Your task is to generate a set of closely related review topics or keywords for a given academic paper based on its title and abstract, and this will help in constructing training data for the model.

### Input
You will be provided with the title and abstract of an academic paper.

### Instructions
Analyze the provided paper's title and abstract, then generate a comprehensive set of review topics that capture the essential aspects of the research. Consider the following angles when generating topics:

1. Analyze the paper's title and abstract to identify core themes, contributions, and context.  
2. Generate 5 review topics or keywords that are tightly related to the paper. These should reflect aspects such as:  
   - **Research field**: The broad domain or discipline (e.g., "machine learning," "computational biology").  
   - **Research methods**: The methodologies employed (e.g., "deep learning," "empirical analysis," "simulation-based studies").  
   - **Proposed method categories**: Specific techniques or approaches introduced (e.g., "reinforcement learning algorithms," "data augmentation strategies").  
   - **Research value**: The practical or theoretical significance (e.g., "applications in healthcare," "theoretical foundations of AI").  
   - **Main contributions**: Key novelties or breakthroughs (e.g., "neural network architectures," "cross-disciplinary integration").  
3. Ensure topics are specific, relevant, and representative of the paper's content. Avoid overly broad or generic terms.  
4. If the paper lacks clear information in certain angles, focus on the most prominent aspects.  

**Output Format:**  
Return the results in JSON format with the following structure:  
```json  
{{  
  "review_topics": ["topic1", "topic2", "topic3", ...]
}}  
```  

**Example:**  
For a paper titled "Attention Is All You Need" with an abstract discussing transformer models, your output might look like:  
```json  
{{  
  "review_topics": ["transformer models", "attention mechanisms in NLP", "neural network architectures", "sequence-to-sequence learning"]  
}}  
```  

Now, process the following paper and provide your response in the specified JSON format.  
- Title: {x['title']}  
- Abstract: {x['abstract']}  

"""
    return [{'role': 'user', 'content': prompt}]