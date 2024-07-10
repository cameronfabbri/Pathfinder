"""
"""
import os
import json
import pprint

from collections import defaultdict

import autogen

from autogen import (AssistantAgent, ConversableAgent, GroupChat,
                     GroupChatManager, UserProxyAgent)
from autogen.agentchat import (AssistantAgent, GroupChat, GroupChatManager,
                               UserProxyAgent)
from autogen.graph_utils import visualize_speaker_transitions_dict
from autogen.oai.openai_utils import config_list_from_dotenv

from src import prompts


def build_llm_chat_client(
        model: str = constants.DEFAULT_MODEL) -> Callable[[list[Message]], str]:
    """Make an LLM client that accepts a list of messages and returns a response."""
    if 'gpt' in model:
        client = openaiapi.get_openaiai_client()
        chat_session = openaiapi.start_chat(model, client)

        def chat(messages: list[Message]) -> Message:
            return chat_session(messages)

    return chat


class PathFinder:

    def __init__(self):

        self.openai_api_key = os.environ['OPENAI_API_KEY']
        #self.model = 'gpt-3.5-turbo'
        self.model = 'gpt-4o'
        self.llm_config = {
            "config_list": [
                {
                    "model": self.model, "api_key": self.openai_api_key
                }
            ]
        }

        self.manager = ConversableAgent(
            name='ConversationManager',
            system_message=prompts.CONVERSATION_MANAGER_SYSTEM_PROMPT,
            llm_config=self.llm_config,
            human_input_mode='NEVER'
        )

        # The user interacting with the system
        self.student_agent = autogen.UserProxyAgent(
            name="StudentAgent",
            system_message='',
            llm_config=self.llm_config,
            human_input_mode='ALWAYS'
        )

        self.counselor_agent = AssistantAgent(
            name='PathFinderCounselor',
            system_message=prompts.COUNSELOR_SYSTEM_PROMPT,
            llm_config=self.llm_config,
            human_input_mode='NEVER'
        )

        self.career_agent = AssistantAgent(
            name="CareerAgent",
            llm_config=self.llm_config,
            system_message="""
            CareerAgent. Your job is to chat with the PathFinderCounselor Agent to obtain information about their student. From the information you will provide career guidance based on their skills, interests, personality traits, and academic performance.
            """
        )

    def speaker_selection_func(self, last_speaker, conversation_history):

        next_speaker = self.counselor_agent

        #print('last_speaker:', last_speaker.name)

        #response = conversation_history[-1][1].chat_history[-1]['content']
        #print('response:', response)
        #exit()

        # Student always talks to the counselor
        if last_speaker == self.student_agent:
            next_speaker = self.counselor_agent

        # Check if the counselor needs to contact an external agent
        elif last_speaker == self.counselor_agent:
            next_speaker = self.student_agent

        #elif last_speaker == self.career_agent:
        #    next_speaker = self.counselor_agent

        print('conversation history')
        print(conversation_history, '\n')
        #exit()
        #print('messages')
        #print(last_speaker.chat_messages)
        #print('next_speaker:', next_speaker.name)
        #print('\n', '*' * 50, '\n')
        print('next_speaker:', next_speaker.name, '\n')
        return next_speaker

    def run(self):

        current_speaker = self.student_agent
        initial_message = 'Good morning'

        # Student initiates the conversation
        #response = current_speaker.initiate_chat(
        #    recipient=self.counselor_agent,
        #    message=initial_message,
        #    summary_method="last_msg",
        #)

        i = 0
        while True:
            message = input('> ')
            if message == 'exit':
                break
            request_reply = True

            self.student_agent.send(
                message, self.counselor_agent, request_reply=False
            )
            print(self.counselor_agent.chat_messages)
            print('\n')
            i += 1

            #print('STUDENT AGENT')
            #print(self.student_agent.chat_messages, '\n')
            #print('COUNSELOR')
            #print(self.counselor_agent.chat_messages, '\n')
            #print('\n', '$' * 80, '\n')

            #history = self.counselor_agent.chat_messages
            #print('HISTORY')
            #print(history, '\n')
            #print('UPDATE')
            #)
            #print(history, '\n')
            #print('\n', '$' * 80, '\n')

        #print(self.counselor_agent.chat_messages_for_summary(self.student_agent))


def main():

    pathfinder = PathFinder()
    pathfinder.run()

    # Print the summary of the conversation
    #pprint.pprint(chat_result.summary)

    #pprint.pprint(chat_result.chat_history)


if __name__ == '__main__':
    main()
