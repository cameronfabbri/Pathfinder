"""
"""

import sys
import click
from datetime import datetime

import src.database.db_access as dba
from src.utils import get_color, RESET

def fetch_conversation_history(user_id: int | None = None, session_id: int | None = None):
    """
    Fetches the conversation history for a given user ID.

    Args:
        user_id (int): The ID of the user.

    Returns:
        list: A list of conversation messages.
    """
    conn = dba.get_user_db_connection(user_id)
    cursor = conn.cursor()
    if session_id is not None:
        cursor.execute("""
            SELECT sender, recipient, message, session_id, chat_id, timestamp, tool_call FROM conversation_history
            WHERE session_id = ?
            ORDER BY timestamp ASC
        """, (session_id,))
    else:
        cursor.execute("""
            SELECT sender, recipient, message, session_id, chat_id, timestamp, tool_call FROM conversation_history
            ORDER BY timestamp ASC
        """)
    conversation_history = cursor.fetchall()
    return conversation_history


def format_and_print_conversation(conversation_history):
    """
    Formats and prints the conversation history in a readable manner.

    Args:
        conversation_history (list): List of conversation messages.
    """
    print("\nConversation History:")
    print("=" * 60)

    for (sender, recipient, message, session_id, chat_id, timestamp, tool_call) in conversation_history:

        # Convert timestamp to a readable format if needed
        timestamp = datetime.strptime(timestamp, '%Y-%m-%d %H:%M:%S')

        print(f"Session ID: {session_id}, Chat ID: {chat_id}")
        sender_color = get_color(sender)
        recipient_color = get_color(recipient)
        print(f"[{timestamp}] {sender_color}{sender}{RESET} -> {recipient_color}{recipient}{RESET}: {message}")
        if tool_call:
            print(f"Tool Call: {tool_call}")
        print("-" * 60)


@click.command()
@click.option('--user_id', '-u', type=int, default=None, help='The ID of the user to fetch the conversation history for.')
@click.option('--session_id', '-s', type=int, default=None, help='The ID of the session to fetch the conversation history for.')
def main(user_id, session_id):

    conversation_history = fetch_conversation_history(user_id, session_id)

    if conversation_history:
        format_and_print_conversation(conversation_history)
    else:
        print(f"No conversation history found for user ID {user_id}.")


if __name__ == "__main__":
    main()