from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

def estimate_tokens(text: str) -> int:
    text = text.strip()
    if not text:
        return 0
    # Simple heuristic: 1 token ~ 4 characters
    return max(1, len(text) // 4)

@dataclass
class UserProfileStore:
    root_dir: Path

    def __post_init__(self):
        self.root_dir.mkdir(parents=True, exist_ok=True)

    def path_for(self, user_id: str) -> Path:
        safe_id = re.sub(r'[^a-zA-Z0-9_-]', '_', user_id)
        return self.root_dir / f"{safe_id}.md"

    def read_text(self, user_id: str) -> str:
        path = self.path_for(user_id)
        if path.exists():
            return path.read_text(encoding="utf-8")
        return "# User Profile\n\nNo facts available."

    def write_text(self, user_id: str, content: str) -> Path:
        path = self.path_for(user_id)
        path.write_text(content, encoding="utf-8")
        return path

    def edit_text(self, user_id: str, search_text: str, replacement: str) -> bool:
        content = self.read_text(user_id)
        if search_text in content:
            new_content = content.replace(search_text, replacement)
            self.write_text(user_id, new_content)
            return True
        return False

    def file_size(self, user_id: str) -> int:
        path = self.path_for(user_id)
        if path.exists():
            return path.stat().st_size
        return 0

def extract_profile_updates(message: str) -> dict[str, str]:
    facts = {}
    
    match_name = re.search(r'(tên tôi là|mình là|tên mình là|tên là)\s+([A-Z][a-zA-Z]*(\s+[A-Z][a-zA-Z]*)*|\w+)', message, re.IGNORECASE)
    if match_name:
        facts["name"] = match_name.group(2).strip()
        
    match_loc = re.search(r'(chuyển đến sống ở|chuyển tới|sống ở|ở lại|ở)\s+([A-Z][a-zA-Z\s]+)', message, re.IGNORECASE)
    if match_loc:
        loc = match_loc.group(2).strip()
        loc = re.split(r'\b(và|nhưng|hoặc|,|\.)\b', loc)[0].strip()
        facts["location"] = loc
        
    match_prof = re.search(r'(làm nghề|làm công việc|là một|làm)\s+([a-zA-Z\s]+)', message, re.IGNORECASE)
    if match_prof:
        prof = match_prof.group(2).strip()
        prof = re.split(r'\b(và|nhưng|hoặc|,|\.)\b', prof)[0].strip()
        if prof.lower() not in ["việc", "gì", "sao"]:
            facts["profession"] = prof
            
    match_pref = re.search(r'(rất thích|thích|ưa chuộng)\s+(.+)', message, re.IGNORECASE)
    if match_pref:
        pref = match_pref.group(2).strip()
        pref = re.split(r'\b(và|nhưng|hoặc|,|\.)\b', pref)[0].strip()
        if pref:
            facts["preference"] = pref
            
    return facts

def summarize_messages(messages: list[dict[str, str]], max_items: int = 6) -> str:
    if not messages:
        return ""
    recent = messages[-max_items:]
    summary = f"[Summarized {len(messages)} older messages]\n"
    # only keep very short snippet
    for msg in recent:
        summary += f"- {msg['role']}: {msg['content'][:20]}...\n"
    return summary

@dataclass
class CompactMemoryManager:
    threshold_tokens: int
    keep_messages: int
    state: dict[str, dict[str, object]] = field(default_factory=dict)

    def append(self, thread_id: str, role: str, content: str) -> None:
        if thread_id not in self.state:
            self.state[thread_id] = {
                "messages": [],
                "summary": "",
                "compactions": 0,
                "token_usage": 0
            }
            
        thread_state = self.state[thread_id]
        msg = {"role": role, "content": content}
        thread_state["messages"].append(msg)
        
        total_tokens = estimate_tokens(thread_state["summary"]) + sum(estimate_tokens(m["content"]) for m in thread_state["messages"])
        thread_state["token_usage"] = total_tokens
        
        if total_tokens > self.threshold_tokens and len(thread_state["messages"]) > self.keep_messages:
            msgs_to_summarize = thread_state["messages"][:-self.keep_messages]
            kept_msgs = thread_state["messages"][-self.keep_messages:]
            
            new_summary = summarize_messages(msgs_to_summarize)
            if thread_state["summary"]:
                # Keep summary bounded
                thread_state["summary"] = thread_state["summary"][-500:] + "\n" + new_summary
            else:
                thread_state["summary"] = new_summary
                
            thread_state["messages"] = kept_msgs
            thread_state["compactions"] += 1
            thread_state["token_usage"] = estimate_tokens(thread_state["summary"]) + sum(estimate_tokens(m["content"]) for m in thread_state["messages"])

    def context(self, thread_id: str) -> dict[str, object]:
        if thread_id not in self.state:
            return {"messages": [], "summary": "", "compactions": 0, "token_usage": 0}
        return self.state[thread_id]

    def compaction_count(self, thread_id: str) -> int:
        if thread_id in self.state:
            return self.state[thread_id]["compactions"]
        return 0
