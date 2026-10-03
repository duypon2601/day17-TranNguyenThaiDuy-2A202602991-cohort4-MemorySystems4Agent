from __future__ import annotations

import os
from pathlib import Path

from agent_advanced import AdvancedAgent
from agent_baseline import BaselineAgent
from config import LabConfig
from model_provider import ProviderConfig
from memory_store import UserProfileStore


def make_config(tmp_path: Path):
    model_config = ProviderConfig(
        provider="openai",
        model_name="gpt-4o-mini",
        temperature=0.0
    )
    
    return LabConfig(
        base_dir=tmp_path,
        data_dir=tmp_path / "data",
        state_dir=tmp_path / "state",
        compact_threshold_tokens=50,
        compact_keep_messages=1,
        model=model_config,
        judge_model=model_config
    )


def test_user_markdown_read_write_edit(tmp_path: Path) -> None:
    store = UserProfileStore(tmp_path / "profiles")
    
    # Read non-existent
    content = store.read_text("test_user")
    assert "No facts available" in content
    
    # Write
    store.write_text("test_user", "My name is John.")
    assert store.read_text("test_user") == "My name is John."
    
    # Edit
    changed = store.edit_text("test_user", "John", "Doe")
    assert changed is True
    assert store.read_text("test_user") == "My name is Doe."


def test_compact_trigger(tmp_path: Path) -> None:
    config = make_config(tmp_path)
    agent = AdvancedAgent(config, force_offline=True)
    
    thread_id = "thread_compact"
    
    # Send enough messages to exceed threshold (50 tokens)
    for i in range(10):
        agent.reply("user1", thread_id, f"Hello, this is a somewhat long message number {i} to trigger compaction process.")
        
    assert agent.compaction_count(thread_id) > 0


def test_cross_session_recall(tmp_path: Path) -> None:
    config = make_config(tmp_path)
    advanced = AdvancedAgent(config, force_offline=True)
    baseline = BaselineAgent(config, force_offline=True)
    
    # 1. Inform in thread A
    advanced.reply("user1", "thread_a", "Tên tôi là Alice.")
    baseline.reply("user1", "thread_a", "Tên tôi là Alice.")
    
    # 2. Recall in thread B
    adv_resp = advanced.reply("user1", "thread_b", "Tên tôi là gì?")
    base_resp = baseline.reply("user1", "thread_b", "Tên tôi là gì?")
    
    assert "Alice" in adv_resp["content"]
    assert "Alice" not in base_resp["content"]


def test_compact_reduces_prompt_load_on_long_thread(tmp_path: Path) -> None:
    config = make_config(tmp_path)
    advanced = AdvancedAgent(config, force_offline=True)
    baseline = BaselineAgent(config, force_offline=True)
    
    thread_id = "long_thread"
    
    # Send messages
    for i in range(20):
        advanced.reply("user1", thread_id, f"This is message number {i} to build up context.")
        baseline.reply("user1", thread_id, f"This is message number {i} to build up context.")
        
    # Baseline prompt load should be strictly greater than Advanced since Advanced compacts
    assert baseline.prompt_token_usage(thread_id) > advanced.prompt_token_usage(thread_id)
