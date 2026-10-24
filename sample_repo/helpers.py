def format_timestamp(epoch_seconds):
    from datetime import datetime, timezone
    dt = datetime.fromtimestamp(epoch_seconds, tz=timezone.utc)
    return dt.isoformat()

def sanitize_slug(input_text):
    import re
    cleaned = re.sub(r'[^a-zA-Z0-9_-]', '-', input_text.strip().lower())
    return re.sub(r'-+', '-', cleaned)
