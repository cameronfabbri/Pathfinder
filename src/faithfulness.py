"""
Functions for calculating faithfulness of a RAG system.
Based on the RAGAS library.
"""

from typing import Callable, List, Tuple, Dict, Any
import json

import numpy as np


def generate_statments_prompt(question: str, answer: str) -> str:
    """
    Generate statements from an answer.
    Based on the faithfulness implementation in https://github.com/explodinggradients/ragas
    """

    template = """
    Your task is to create one or more statements from each sentence in the given answer.
    
    question: Who was  Albert Einstein and what is he best known for?
    answer: He was a German-born theoretical physicist, widely acknowledged to be one of the greatest and most influential physicists of all time. He was best known for developing the theory of relativity, he also made important contributions to the development of the theory of quantum mechanics.
    statements in json:
    {
        "statements": [
            "Albert Einstein was born in Germany.",
            "Albert Einstein was best known for his theory of relativity."
        ]
    }
    
    question: Cadmium Chloride is slightly soluble in this chemical, it is also called what?
    answer: alcohol
    statements in json:
    {
        "statements": [
            "Cadmium Chloride is slightly soluble in alcohol."
        ]
    }
    
    question: Were Hitler and Benito Mussolini of the same nationality?
    answer: Sorry, I can't provide answer to that question.
    statements in json:
    {
        "statements": []
    }
    """

    return cleanup(template) + (
        f'question: {question}\n' +
        f'answer: {answer}\n' +
        'statements in json:'
    )


def evaluate_statements_prompt(context: str, statements: List[str]) -> str:
    """
    Evaluate statements.
    Based on the faithfulness implementation in https://github.com/explodinggradients/ragas
    """

    template = """
    Your task is to evaluate whether each statement is supported by the context. Only use "Yes" or "No" as verdict.

    Context:
    John is a student at XYZ University. He is pursuing a degree in Computer Science. He is enrolled in several courses this semester, including Data Structures, Algorithms, and Database Management. John is a diligent student and spends a significant amount of time studying and completing assignments. He often stays late in the library to work on his projects.
    statement_1: John is majoring in Biology.
    statement_2: John is taking a course on Artificial Intelligence. 
    statement_3: John is a dedicated student. 
    statement_4: John has a part-time job.
    Answer:
    [
        {
            "statement_1": "John is majoring in Biology.",
            "reason": "John's major is explicitly mentioned as Computer Science. There is no information suggesting he is majoring in Biology.",
            "verdict": "No"
        },
        {
            "statement_2": "John is taking a course on Artificial Intelligence.",
            "reason": "The context mentions the courses John is currently enrolled in, and Artificial Intelligence is not mentioned. Therefore, it cannot be deduced that John is taking a course on AI.",
            "verdict": "No"
        },
        {
            "statement_3": "John is a dedicated student.",
            "reason": "The context states that he spends a significant amount of time studying and completing assignments. Additionally, it mentions that he often stays late in the library to work on his projects, which implies dedication.",
            "verdict": "Yes"
        },
        {
            "statement_4": "John has a part-time job.",
            "reason": "There is no information given in the context about John having a part-time job.",
            "verdict": "No"
        }
    ]
    
    Context:
    Photosynthesis is a process used by plants, algae, and certain bacteria to convert light energy into chemical energy.
    statement_1: Albert Einstein was a genius.
    Answer:
    [
         {
            "statement_1": "Albert Einstein was a genius.",
            "reason": "The context and statement are unrelated."
            "verdict": "No"
        }
    ]
    
    """

    return cleanup(template) + (
        f'Context:\n{context}\n' +
        'Statements:\n' +
        '\n'.join([f'statement_{idx + 1}: {x}' for idx, x in enumerate(statements)]) + '\n' +
        f'Answer:\n'
    )


def cleanup(x: str) -> str:
    """Remove leading spaces from triple-quoted strings."""
    lines = x.splitlines()
    lines = [x.lstrip() for x in lines]
    return '\n'.join(lines)


def faithfulness(
        question: str,
        docs: str,
        answer: str,
        llm: Callable
        ) -> Tuple[float, List[Dict], List[float]]:
    """
    Given RAG inputs and outputs, calculate faithfulness.
    """

    # TODO: handle additional error cases

    prompt = generate_statments_prompt(question, answer)
    response = llm(prompt)
    print(response)

    statements: List[Dict] = _parse_json(response)['statements']
    if not statements:
        return np.nan, [], []

    prompt = evaluate_statements_prompt(docs, statements)

    verdicts: List[Dict] = _parse_json(llm(prompt))

    verdict_scores_map = {
        'yes': 1.,
        'no': 0.
    }

    scores = []
    for verdict_info in verdicts:
        verdict = verdict_info.get('verdict', '').lower()
        score = verdict_scores_map.get(verdict, np.nan)
        scores.append(score)

    total_score = sum(scores) / len(scores)

    return total_score, verdicts, scores


def _parse_json(x: str) -> Any:
    if x.startswith('```json') and x.endswith('```'):
        x = x[7:-3]
    return json.loads(x)
