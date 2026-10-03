from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from config import LabConfig, load_config
from memory_store import estimate_tokens


@dataclass
class SessionState:
    messages: list[dict[str, str]] = field(default_factory=list)
    token_usage: int = 0
    prompt_tokens_processed: int = 0


class BaselineAgent:
    def __init__(self, config: LabConfig | None = None, force_offline: bool = False) -> None:
        self.config = config or load_config()
        self.force_offline = force_offline
        self.sessions: dict[str, SessionState] = {}

    def reply(self, user_id: str, thread_id: str, message: str) -> dict[str, Any]:
        return self._reply_offline(thread_id, message)

    def token_usage(self, thread_id: str) -> int:
        return self.sessions.get(thread_id, SessionState()).token_usage

    def prompt_token_usage(self, thread_id: str) -> int:
        return self.sessions.get(thread_id, SessionState()).prompt_tokens_processed

    def compaction_count(self, thread_id: str) -> int:
        return 0

    def memory_file_size(self, user_id: str) -> int:
        return 0

    def _reply_offline(self, thread_id: str, message: str) -> dict[str, Any]:
        if thread_id not in self.sessions:
            self.sessions[thread_id] = SessionState()
            
        session = self.sessions[thread_id]
        
        prompt_tokens = sum(estimate_tokens(m["content"]) for m in session.messages) + estimate_tokens(message)
        session.prompt_tokens_processed += prompt_tokens
        
        session.messages.append({"role": "user", "content": message})
        
        # Determine dummy answer based on thread's short term memory
        answer = "Tôi đã hiểu."
        
        # Extremely simple heuristics for offline benchmark responses
        # If asked a question in the same thread, scan previous messages for answers.
        if "Tên mình là gì" in message or "tên" in message.lower():
            for m in reversed(session.messages):
                if "tên là" in m["content"].lower() or "mình là" in m["content"].lower():
                    answer = f"Tên của bạn là {m['content']}"
                    break
                    
        elif "nghề" in message.lower() or "làm gì" in message.lower():
            for m in reversed(session.messages):
                if "làm nghề" in m["content"].lower() or "là một" in m["content"].lower():
                    answer = f"Nghề nghiệp của bạn liên quan đến {m['content']}"
                    break
                    
        elif "sống ở" in message.lower() or "ở đâu" in message.lower():
            for m in reversed(session.messages):
                if "sống ở" in m["content"].lower() or "chuyển đến" in m["content"].lower():
                    answer = f"Bạn đang ở {m['content']}"
                    break
                    
        elif "thích" in message.lower():
            for m in reversed(session.messages):
                if "thích" in m["content"].lower():
                    answer = f"Bạn thích {m['content']}"
                    break
        
        session.messages.append({"role": "assistant", "content": answer})
        
        agent_tokens = estimate_tokens(answer)
        session.token_usage += agent_tokens
        
        return {"content": answer}

    def _maybe_build_langchain_agent(self):
        pass
