"""
"""
import os
import json
from datetime import datetime


def format_content(content):
    if isinstance(content, str):
        try:
            return json.dumps(json.loads(content), indent=2)
        except json.JSONDecodeError:
            return content
    elif isinstance(content, dict):
        return json.dumps(content, indent=2)
    return str(content)


def log_messages(agent_name, messages):
    """
    Log messages to a timestamped text file in the 'logs/' directory.
    
    Args:
        agent_name (str): Name of the agent (e.g., 'counselor', 'suny')
        messages (list): List of message dictionaries
    """
    os.makedirs('logs', exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d")
    filename = f"logs/{agent_name}_chat_{timestamp}.txt"
    
    with open(filename, 'a', encoding='utf-8') as f:
        f.write(f"\n--- New Interaction: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ---\n")
        for message in messages:
            f.write(f"Role: {message['role']}\n")
            if 'content' in message and message['content'] is not None:
                f.write("Content:\n")
                f.write(f"{format_content(message['content'])}\n\n")
            if 'tool_calls' in message:
                f.write("Tool Calls:\n")
                for tool_call in message['tool_calls']:
                    f.write(f"Tool: {tool_call['function']['name']}\n")
                    f.write(f"Arguments: {format_content(tool_call['function']['arguments'])}\n\n")
            if 'tool_call_id' in message:
                f.write(f"Tool Call ID: {message['tool_call_id']}\n")
            f.write("-" * 50 + "\n")


def append_message(agent_name, message):
    """
    Append a single message to the most recent log file for the given agent.
    
    Args:
        agent_name (str): Name of the agent (e.g., 'counselor', 'suny')
        message (dict): Message dictionary to append
    """
    # Find the most recent log file for this agent
    log_files = [f for f in os.listdir('logs') if f.startswith(f"{agent_name}_chat_")]
    if not log_files:
        # If no log file exists, create a new one
        log_messages(agent_name, [message])
        return
    
    most_recent_file = max(log_files)
    filepath = os.path.join('logs', most_recent_file)
    
    # Append the message to the file
    with open(filepath, 'a', encoding='utf-8') as f:
        f.write(f"{message['role']}: {message['content']}\n\n")