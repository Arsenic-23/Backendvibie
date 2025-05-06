def generate_stream_id(stream_type: str, owner_id: int) -> str:
    """Generates a unique stream ID based on stream type and owner ID."""
    prefix = "g" if stream_type == "group" else "u"
    return f"{prefix}{owner_id}"

def generate_deep_link(stream_id: str) -> str:
    """Generates a deep link for users to join the stream."""
    return f"https://t.me/vibie_bot/Vibiebot/join/{stream_id}"