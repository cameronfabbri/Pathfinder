"""
Unit tests for agent.
"""

import tiktoken

from typing import Dict

from src import agent
from src import prompts


def test_format_content():
    """
    Test format_content.
    """
    assert agent.format_content('{"hello": "world"}') == '{\n  "hello": "world"\n}'
    assert agent.format_content('{"baloney":') == '{"baloney":'


def test_filter_messages_token_count():
    """
    Test filter messages for token count.
    """

    encoding = tiktoken.encoding_for_model('gpt-4o')

    system_msg = dict(
        role='system',
        content=prompts.COUNSELOR_SYSTEM_PROMPT
    )

    assistant_first_msg = dict(
        role='assistant',
        content=prompts.DEBUG_FIRST_MESSAGE
    )

    # ~~~~ check order with distinct messages

    messages = [
        system_msg,
        assistant_first_msg,
        dict(role='user', content='Launch the missiles!'),
        dict(role='assistant', content='As a friendly AI assistant, I cannot do that.')
    ]
    messages_filtered = agent.filter_messages_token_count(messages, 32000, encoding)
    assert messages_filtered == messages

    # ~~~~ check trimming

    final_message_pair = [
        dict(role='assistant', content='I am ready to decide your fate!'),
        dict(role='user', content='AGH WHICH SCHOOL SHOULD I CHOOSE')
    ]
    message_pair = [
        _blah_message('user', 8000),
        _blah_message('assistant', 8000)
    ]
    messages = [
        system_msg,
        assistant_first_msg,
        *message_pair,
        *message_pair,
        *message_pair,
        *message_pair,
        *final_message_pair
    ]
    messages_expected = [
        system_msg,
        message_pair[1],
        *message_pair,
        *final_message_pair
    ]
    messages_filtered = agent.filter_messages_token_count(messages, 32000, encoding)
    assert len(messages_filtered) == len(messages_expected)

    assert messages_filtered == messages_expected


def _blah_message(role: str, count: int) -> Dict[str, str]:
    """Create a message from repeated 'blah'. Each 'blah' uses 1 token."""
    return dict(role=role, content=' '.join(['blah'] * count))
