"""
"""
import os
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


class Student:

    def __init__(self):

        self.first_name = ''
        self.last_name = ''
        self.about = ''


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

        self.graph_dict = {
            self.student_agent: [self.counselor_agent],
            self.counselor_agent: [self.student_agent, self.career_agent]
        }

        self.agents = [self.counselor_agent, self.student_agent, self.career_agent]

        def custom_speaker_selection_func(last_speaker, group_chat):

            print('last_speaker:', last_speaker.name)

            # Student always talks to the counselor
            if last_speaker == self.student_agent:
                next_speaker = self.counselor_agent

            # Check if the counselor needs to contact an external agent
            elif last_speaker == self.counselor_agent:
                next_speaker = self.student_agent

            elif last_speaker == self.career_agent:
                next_speaker = self.counselor_agent

            print('groupchat messages')
            print(group_chat.messages, '\n\n')

            # Determine if the counselor should respond, or if it needs to chat
            # with another agent
            if 'career' in group_chat.messages[-1]['content']:
                return self.career_agent

            #print('messages')
            #print(last_speaker.chat_messages)
            #print('next_speaker:', next_speaker.name)
            #print('\n', '*' * 50, '\n')

            return next_speaker

        # create the groupchat
        #group_chat = GroupChat(
        #    agents=self.agents,
        #    messages=[],
        #    max_round=25,
        #    allowed_or_disallowed_speaker_transitions=self.graph_dict,
        #    allow_repeat_speaker=None,
        #    speaker_transitions_type="allowed",
        #    speaker_selection_method=custom_speaker_selection_func
        #)

        #self.manager = GroupChatManager(
        #    groupchat=group_chat,
        #    llm_config=self.llm_config,
        #    is_termination_msg=lambda x: x.get("content", "") and x.get("content", "").rstrip().endswith("TERMINATE"),
        #    code_execution_config=False,
        #)

        #print(dir(self.manager))
        #print(self.manager.description, '\n')
        #self.manager.update_system_message('Update message')
        #print(self.manager.system_message, '\n')

    def run(self):

        self.student_agent.initiate_chat(
            self.counselor_agent,
            message="Good morning",
            clear_history=False
        )
        exit()

        i = 0
        while True:
            message = input('> ')
            if message == 'exit':
                break
            request_reply = True

            out = self.student_agent.send(
                message, self.counselor_agent, request_reply=request_reply
            )
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

            if i == 2:

                summary_args = {
                    'summary_prompt': "Summarize the takeaway from the conversation. Do not add any introductory phrases."
                }
                summary = self.counselor_agent._summarize_chat(
                    summary_method='reflection_with_llm',
                    summary_args=summary_args,
                    recipient=self.counselor_agent
                )
                print('SUMMARY')
                print(summary)
                exit()

                '''
                history = self.counselor_agent.chat_messages

                history[self.student_agent].append(
                    {'content': 'my favorite number is 7', 'role': 'user'}
                )
                history[self.student_agent].append(
                    {'content': 'What\'s my favorite number?', 'role': 'user'}
                )

                message_to_send = {
                    'content': [
                        {
                            'text': 'my favorite number is 7',
                            'role': 'user',
                            'type': 'text'
                        },
                        {
                            'text': 'What\'s my favorite number?',
                            'role': 'user',
                            'type': 'text'
                        }
                    ],
                    'role': 'user',
                }

                print(history, '\n')
                print('message')
                print(message_to_send)
                exit()

                self.student_agent.send(
                    message_to_send,
                    self.career_agent,
                    request_reply=1
                )
                '''

        #print(self.counselor_agent.chat_messages_for_summary(self.student_agent))


def main():

    pathfinder = PathFinder()
    pathfinder.run()

    # Print the summary of the conversation
    #pprint.pprint(chat_result.summary)

    #pprint.pprint(chat_result.chat_history)


if __name__ == '__main__':
    main()

'''
assessment_agent = ConversableAgent(
    name="AssessmentAgent",
    system_message="""Your job is to evaluate a student's skills, interests, personality traits, and academic performance to provide personalized recommendations and insights. Be sure to ask questions in order to obtain all of the following information: grades, favorite subjects, least favorite subjects, interests, hobbies, clubs and extracurricular activities, personality traits, strengths, weaknesses. Once an assessment has been completed, interact with the CareerAgent to discuss potential career options.""",
    llm_config=llm_config,
    human_input_mode='NEVER'
)

profile_agent = ConversableAgent(
    name="ProfileAgent",
    system_message="""ProfileAgent. Your job is to infer the assessment on a student and create/update a personalized profile for them.""",
    llm_config=llm_config,
    human_input_mode='NEVER'
)
'''
