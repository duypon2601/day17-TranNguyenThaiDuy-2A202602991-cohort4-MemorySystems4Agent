from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from tabulate import tabulate

from agent_advanced import AdvancedAgent
from agent_baseline import BaselineAgent
from config import load_config


@dataclass
class BenchmarkRow:
    agent_name: str
    agent_tokens_only: int
    prompt_tokens_processed: int
    recall_score: float
    response_quality: float
    memory_growth_bytes: int
    compactions: int


def load_conversations(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def recall_points(answer: str, expected: list[str]) -> float:
    if not expected:
        return 1.0
    matched = sum(1 for exp in expected if exp.lower() in answer.lower())
    return matched / len(expected)


def heuristic_quality(answer: str, expected: list[str]) -> float:
    # A lightweight quality score for offline
    return recall_points(answer, expected)


def run_agent_benchmark(agent_name: str, agent, conversations: list[dict[str, Any]], config) -> BenchmarkRow:
    total_recall = 0.0
    total_quality = 0.0
    total_prompt_tokens = 0
    total_agent_tokens = 0
    total_compactions = 0
    total_memory_growth = 0
    
    questions_count = 0
    
    for conv in conversations:
        thread_id = conv["id"]
        user_id = conv["user_id"]
        
        # 1. Feed all turns to the agent
        for turn in conv["turns"]:
            agent.reply(user_id, thread_id, turn)
            
        # 2. Ask recall questions in a fresh thread
        recall_thread = thread_id + "_recall"
        for q_obj in conv.get("recall_questions", []):
            question = q_obj["question"]
            expected = q_obj["expected_contains"]
            
            resp = agent.reply(user_id, recall_thread, question)
            answer = resp["content"]
            
            points = recall_points(answer, expected)
            qual = heuristic_quality(answer, expected)
            
            total_recall += points
            total_quality += qual
            questions_count += 1
            
        # Accumulate metrics
        total_agent_tokens += agent.token_usage(thread_id)
        total_prompt_tokens += agent.prompt_token_usage(thread_id)
        total_compactions += agent.compaction_count(thread_id)
        total_memory_growth = max(total_memory_growth, agent.memory_file_size(user_id))

    avg_recall = total_recall / questions_count if questions_count > 0 else 0.0
    avg_qual = total_quality / questions_count if questions_count > 0 else 0.0

    return BenchmarkRow(
        agent_name=agent_name,
        agent_tokens_only=total_agent_tokens,
        prompt_tokens_processed=total_prompt_tokens,
        recall_score=avg_recall,
        response_quality=avg_qual,
        memory_growth_bytes=total_memory_growth,
        compactions=total_compactions,
    )


def format_rows(rows: list[BenchmarkRow]) -> str:
    headers = ["Agent Name", "Agent tokens only", "Prompt tokens processed", "Cross-session recall", "Response quality", "Memory growth (bytes)", "Compactions"]
    table = []
    for row in rows:
        table.append([
            row.agent_name,
            row.agent_tokens_only,
            row.prompt_tokens_processed,
            f"{row.recall_score:.2f}",
            f"{row.response_quality:.2f}",
            row.memory_growth_bytes,
            row.compactions
        ])
    return tabulate(table, headers, tablefmt="github")


def main() -> None:
    config = load_config(Path(__file__).resolve().parent.parent)

    std_path = config.data_dir / "conversations.json"
    stress_path = config.data_dir / "advanced_long_context.json"

    print("Running benchmarks...\n")

    # Standard Benchmark
    std_convs = load_conversations(std_path)
    if std_convs:
        baseline_std = BaselineAgent(config, force_offline=True)
        advanced_std = AdvancedAgent(config, force_offline=True)
        
        row_b_std = run_agent_benchmark("Baseline", baseline_std, std_convs, config)
        row_a_std = run_agent_benchmark("Advanced", advanced_std, std_convs, config)
        
        print("### Standard Benchmark")
        print(format_rows([row_b_std, row_a_std]))
        print("\n")
    
    # Long-Context Stress Benchmark
    stress_convs = load_conversations(stress_path)
    if stress_convs:
        baseline_stress = BaselineAgent(config, force_offline=True)
        advanced_stress = AdvancedAgent(config, force_offline=True)
        
        row_b_stress = run_agent_benchmark("Baseline", baseline_stress, stress_convs, config)
        row_a_stress = run_agent_benchmark("Advanced", advanced_stress, stress_convs, config)
        
        print("### Long-Context Stress Benchmark")
        print(format_rows([row_b_stress, row_a_stress]))
        print("\n")

if __name__ == "__main__":
    main()
