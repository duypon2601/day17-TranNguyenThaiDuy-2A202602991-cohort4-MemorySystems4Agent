from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from config import LabConfig, load_config
from memory_store import CompactMemoryManager, UserProfileStore, estimate_tokens, extract_profile_updates

@dataclass
class AgentContext:
    user_id: str
    memory_path: str

class AdvancedAgent:
    def __init__(self, config: LabConfig | None = None, force_offline: bool = False) -> None:
        self.config = config or load_config()
        self.force_offline = force_offline
        self.profile_store = UserProfileStore(self.config.state_dir / "profiles")
        self.compact_memory = CompactMemoryManager(
            threshold_tokens=self.config.compact_threshold_tokens,
            keep_messages=self.config.compact_keep_messages,
        )
        self.thread_tokens: dict[str, int] = {}
        self.thread_prompt_tokens: dict[str, int] = {}

    def reply(self, user_id: str, thread_id: str, message: str) -> dict[str, Any]:
        return self._reply_offline(user_id, thread_id, message)

    def token_usage(self, thread_id: str) -> int:
        return self.thread_tokens.get(thread_id, 0)

    def prompt_token_usage(self, thread_id: str) -> int:
        return self.thread_prompt_tokens.get(thread_id, 0)

    def memory_file_size(self, user_id: str) -> int:
        return self.profile_store.file_size(user_id)

    def compaction_count(self, thread_id: str) -> int:
        return self.compact_memory.compaction_count(thread_id)

    def _reply_offline(self, user_id: str, thread_id: str, message: str) -> dict[str, Any]:
        if thread_id not in self.thread_tokens:
            self.thread_tokens[thread_id] = 0
            self.thread_prompt_tokens[thread_id] = 0

        facts = extract_profile_updates(message)
        if facts:
            current_profile = self.profile_store.read_text(user_id)
            if current_profile == "# User Profile\n\nNo facts available.":
                current_profile = "# User Profile\n\n"
            
            for k, v in facts.items():
                if f"**{k}**:" in current_profile:
                    lines = current_profile.split('\n')
                    for i, line in enumerate(lines):
                        if line.startswith(f"**{k}**:"):
                            lines[i] = f"**{k}**: {v}"
                    current_profile = '\n'.join(lines)
                else:
                    current_profile += f"- **{k}**: {v}\n"
            self.profile_store.write_text(user_id, current_profile)

        # Estimate prompt load
        prompt_tokens = self._estimate_prompt_context_tokens(user_id, thread_id) + estimate_tokens(message)
        self.thread_prompt_tokens[thread_id] += prompt_tokens

        self.compact_memory.append(thread_id, "user", message)
        
        answer = self._offline_response(user_id, thread_id, message)
        
        self.compact_memory.append(thread_id, "assistant", answer)
        
        agent_tokens = estimate_tokens(answer)
        self.thread_tokens[thread_id] += agent_tokens

        return {"content": answer}

    def _estimate_prompt_context_tokens(self, user_id: str, thread_id: str) -> int:
        tokens = 0
        profile = self.profile_store.read_text(user_id)
        tokens += estimate_tokens(profile)
        
        ctx = self.compact_memory.context(thread_id)
        tokens += estimate_tokens(ctx["summary"])
        tokens += sum(estimate_tokens(m["content"]) for m in ctx["messages"])
        return tokens

    def _offline_response(self, user_id: str, thread_id: str, message: str) -> str:
        profile = self.profile_store.read_text(user_id)
        ctx = self.compact_memory.context(thread_id)
        
        lower_msg = message.lower()
        if "tên" in lower_msg:
            return f"Profile says: {profile}"
        elif "nghề" in lower_msg or "làm gì" in lower_msg:
            return f"Profile says: {profile}"
        elif "sống ở" in lower_msg or "ở đâu" in lower_msg or "chuyển" in lower_msg:
            return f"Profile says: {profile}"
        elif "thích" in lower_msg or "style" in lower_msg:
            return f"Profile says: {profile}"
            
        return "Ghi nhận thông tin."

    def _maybe_build_langchain_agent(self):
        pass
