def generate_stream_id(stream_type: str, owner_id: int) -> str:
    prefix = "g" if stream_type == "group" else "u"
    return f"{prefix}{owner_id}"

def generate_deep_link(stream_id: str) -> str:
    return f"https://t.me/vibie_bot/Vibiebot/join/{stream_id}"