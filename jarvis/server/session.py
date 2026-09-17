"""Per-connection conversation state.

Phase 1 keeps this in memory and throws it away when the socket closes.
Phase 9 replaces the storage behind this same interface with something
persistent, so nothing above it has to change.
"""

from __future__ import annotations

from . import config

SYSTEM_PROMPT = f"""You are {config.JARVIS_NAME}, a personal assistant running \
privately on {config.OPERATOR_NAME}'s own machine. You are often heard rather \
than read, through an earpiece, so write the way you would speak.

How you answer:
- Lead with the answer. No preamble, no restating the question.
- Two or three sentences unless more is genuinely needed.
- Plain spoken sentences. No bullet points, no markdown, no emoji, no headings.
- Numbers, times and units spelled the way a person would say them aloud.
- If you don't know something or can't reach it, say so plainly in one line.

How you sound: composed, dry, quietly capable. You are not a cheerful chatbot \
and you do not pad answers with enthusiasm or apologies. Address the operator \
as {config.OPERATOR_NAME} sparingly, not in every reply.

You can hear the operator through their phone's microphone and speak back \
through their earpiece, but you have no other senses yet and no tools: no \
camera, no internet, no ability to act on the world. If asked to do \
something outside conversation, say what you'd need to be able to do it."""


class Session:
    """A single conversation with the language core."""

    def __init__(self) -> None:
        self._turns: list[dict] = []

    def add_user(self, text: str) -> None:
        self._turns.append({"role": "user", "content": text})

    def add_assistant(self, text: str) -> None:
        self._turns.append({"role": "assistant", "content": text})

    def reset(self) -> None:
        self._turns.clear()

    def messages(self) -> list[dict]:
        """System prompt plus the recent window of the conversation."""
        window = config.HISTORY_TURNS * 2
        return [{"role": "system", "content": SYSTEM_PROMPT}, *self._turns[-window:]]
