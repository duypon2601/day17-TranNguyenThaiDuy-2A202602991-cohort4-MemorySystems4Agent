from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

from model_provider import ProviderConfig

@dataclass
class LabConfig:
    base_dir: Path
    data_dir: Path
    state_dir: Path
    compact_threshold_tokens: int
    compact_keep_messages: int
    model: ProviderConfig
    judge_model: ProviderConfig

def load_config(base_dir: Path | None = None) -> LabConfig:
    root = (base_dir or Path(__file__).resolve().parent.parent).resolve()
    
    dotenv_path = root / ".env"
    if dotenv_path.exists():
        load_dotenv(dotenv_path)

    state_dir = root / "state"
    state_dir.mkdir(parents=True, exist_ok=True)
    
    data_dir = root / "data"

    provider = os.getenv("LLM_PROVIDER", "openai")
    model_name = os.getenv("LLM_MODEL", "gpt-4o-mini")
    
    api_key = os.getenv(f"{provider.upper()}_API_KEY", os.getenv("OPENAI_API_KEY"))
    base_url = os.getenv(f"{provider.upper()}_BASE_URL", os.getenv("CUSTOM_BASE_URL"))
    
    model_config = ProviderConfig(
        provider=provider,
        model_name=model_name,
        temperature=0.0,
        api_key=api_key,
        base_url=base_url
    )
    
    judge_config = ProviderConfig(
        provider="openai",
        model_name="gpt-4o-mini",
        temperature=0.0,
        api_key=os.getenv("OPENAI_API_KEY")
    )

    return LabConfig(
        base_dir=root,
        data_dir=data_dir,
        state_dir=state_dir,
        compact_threshold_tokens=int(os.getenv("COMPACT_THRESHOLD_TOKENS", "100")),
        compact_keep_messages=int(os.getenv("COMPACT_KEEP_MESSAGES", "2")),
        model=model_config,
        judge_model=judge_config
    )
