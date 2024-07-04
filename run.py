"""
"""
import os
import pprint

import autogen

from autogen import (AssistantAgent, ConversableAgent, GroupChat,
                     GroupChatManager, UserProxyAgent)
from autogen.graph_utils import visualize_speaker_transitions_dict

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")

STUDENT_INIT_MSG = """I am a high school student interested in computers, video games, and sports.
"""


def main():

    llm_config = {
        "config_list": [
            {
                "model": "gpt-4", "api_key": os.environ["OPENAI_API_KEY"]
            }
        ]
    }

    assessment_agent = ConversableAgent(
        name="AssessmentAgent",
        system_message="""AssessmentAgent. Your job is to evaluate a student's skills, interests, personality traits, and academic performance to provide personalized recommendations and insights. Be sure to ask questions in order to obtain all of the following information: grades, favorite subjects, least favorite subjects, interests, hobbies, clubs and extracurricular activities, personality traits, strengths, weaknesses. Once an assessment has been completed, interact with the CareerAgent to discuss potential career options.""",
        llm_config=llm_config
    )

    career_agent = ConversableAgent(
        name="CareerAgent",
        system_message="""CareerAgent. Your job is to infer the assessment on a student and provide career guidance.""",
        llm_config={"config_list": [{"model": "gpt-4", "api_key": os.environ["OPENAI_API_KEY"]}]},
    )

    student_agent = autogen.UserProxyAgent(
        name="StudentAgent",
        system_message="Human high school student. Interact with the AssessmentAgent to perform an initial assessment.",
        llm_config=llm_config
    )

    def state_transition(last_speaker, groupchat):
        messages = groupchat.messages
        if last_speaker == student_agent:
            return assessment_agent
        elif last_speaker == assessment_agent:
            content = messages[-1]["content"].lower()
            if all(keyword in content for keyword in [
                "grades", "favorite subjects", "least favorite subjects", "interests",
                "hobbies", "clubs and extracurricular activities", "personality traits",
                "strengths", "weaknesses"
            ]):
                return career_agent
            return student_agent
        elif last_speaker == career_agent:
            return student_agent

    # Set up the group chat with the custom state transition function
    group_chat = GroupChat(
        agents=[student_agent, assessment_agent, career_agent],
        messages=[],
        max_round=20,
        speaker_selection_method=state_transition,
    )

    # Create the GroupChatManager
    group_chat_manager = GroupChatManager(
        groupchat=group_chat,
        llm_config=llm_config
    )

    print('assessment_agent:', assessment_agent, '\n')
    print('manager:', group_chat_manager)

    exit()

    # Start the conversation
    initial_message = "Hi, I'm here to get some guidance on my future career."
    chat_result = student_agent.initiate_chat(
        group_chat_manager,
        message=initial_message,
        summary_method="reflection_with_llm",
    )

    # Print the summary of the conversation
    print(chat_result.summary)

    pprint.pprint(chat_result.chat_history)


if __name__ == '__main__':
    main()

