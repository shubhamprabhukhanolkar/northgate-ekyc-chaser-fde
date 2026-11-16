"""Extract only subject/body strings from incomplete provider JSON, never raw tokens."""
import re
import time
from ..live import emit


def partial_string(text, key):
    match = re.search(r'"' + re.escape(key) + r'"\s*:\s*"', text)
    if not match:
        return ""
    value, index = [], match.end()
    escapes = {'n': '\n', 'r': '\r', 't': '\t', 'b': '\b', 'f': '\f', '"': '"', '\\': '\\', '/': '/'}
    while index < len(text):
        char = text[index]
        if char == '"':
            break
        if char == '\\':
            index += 1
            if index >= len(text):
                break
            char = text[index]
            if char == 'u':
                digits = text[index+1:index+5]
                if len(digits) != 4 or not re.fullmatch(r'[0-9a-fA-F]{4}', digits):
                    break
                value.append(chr(int(digits, 16)))
                index += 5
                continue
            if char not in escapes:
                break
            char = escapes[char]
        value.append(char)
        index += 1
    return ''.join(value)


class DraftPreview:
    def __init__(self, agent, provider):
        self.agent = agent
        self.provider = provider
        self.text = ""
        self.last_emit = 0
        self.previous = None
        emit("preview_reset", agent=agent, provider=provider, summary="Writing a live, unreviewed draft." if agent == "drafter" else "Refining the live draft's tone and wording.")

    def add(self, text, force=False):
        self.text += text
        if not force and time.monotonic()-self.last_emit < 0.10:
            return
        value = (partial_string(self.text, "subject"), partial_string(self.text, "body"))
        if value != self.previous and any(value):
            emit("draft_preview", agent=self.agent, provider=self.provider, subject=value[0], body=value[1], unreviewed=True)
            self.previous = value
            self.last_emit = time.monotonic()
