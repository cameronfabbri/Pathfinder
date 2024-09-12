"""
"""

import os

from src.database import ChromaDB

opj = os.path.join

suny_tools = [
    {
        "type": "function",
        "function": {
            "name": "show_campus_map",
            "description": "Display the campus map of the chosen SUNY school. Call this if a user asks to see the campus map.",
            "parameters": {
                "type": "object",
                "properties": {
                    "school_name": {
                        "type": "string",
                        "description": "The name of the SUNY school.",
                    },
                },
                "required": ["school_name"],
                "additionalProperties": False,
            },
        }
    },
    {
        "type": "function",
        "function": {
            "name": "retrieve_content_from_question",
            "description": "Retrieve relevant content from the database based on the user's question. Call this if a user asks a question about a specific school or program.",
            "parameters": {
                "type": "object",
                "properties": {
                    "question": {
                        "type": "string",
                        "description": "The user's question about SUNY schools or programs. Reformat this to be a question.",
                    },
                },
                "required": ["question"],
                "additionalProperties": False,
            },
        }
    }
]


def retrieve_content_from_question(question):
    """

    """

    name = 'www.canton.edu'
    path = opj('system_data', 'chromadb')
    db = ChromaDB(path, name)
    results = db.collection.query(
        query_texts=[question],
        n_results=1
    )
    content = results['documents'][0][0]

    return content

    client = OpenAI(api_key=os.getenv("PATHFINDER_OPENAI_API_KEY"))
    system_prompt = 'You are a helpful assistant that can answer questions about the given document.'
    agent = Agent(client, 'Agent', None, system_prompt, model='gpt-4o', json_mode=False)

    prompt = '**Question:**\n'
    prompt += question + '\n\n'
    prompt += '**Document:**\n' + content

    agent.add_message('user', prompt)

    print('Question:', question)
    response = agent.invoke()
    print('Answer:', response.choices[0].message.content)


def show_campus_map(school_name: str):
    return f"Here is the campus map for {school_name}"


function_map = {
    "show_campus_map": show_campus_map,
    "retrieve_content_from_question": retrieve_content_from_question
}
