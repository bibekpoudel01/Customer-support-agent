def format_history(messages: list) -> str:
    """Turns prior turns into 'User: ... / Assistant: ...' lines.
    Handles both plain dict messages and LangChain message objects."""
    lines = []
    for msg in messages[:-1]:
        role_attr = msg.get("role") if isinstance(msg, dict) else getattr(msg, "type", "")
        role = "User" if role_attr in ("human", "user") else "Assistant"
        content = msg.get("content", "") if isinstance(msg, dict) else getattr(msg, "content", "")
        lines.append(f"{role}: {content}")
    return "\n".join(lines)