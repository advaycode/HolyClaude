"""
models.py — Model capability registry and auto-selection.

Central source of truth for all Ollama models: context limits, strengths,
recommended tasks, and quantization info. Used by PromptOptimizer for routing
and TokenBudget for limit calculation.

Usage:
    model = ModelRegistry.select("implement")   # → "gemma3:4b"
    info = ModelRegistry.get("gemma3:4b")
    print(info.context_tokens, info.strengths)

    # Check if a model is available:
    available = ModelRegistry.available_models()
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ModelInfo:
    name: str
    context_tokens: int
    parameters: str             # e.g. "4.3B"
    quantization: str           # e.g. "Q4_K_M"
    strengths: list[str]
    weaknesses: list[str]
    best_for: list[str]         # task types
    pull_command: str
    size_gb: float
    vision: bool = False
    reasoning: bool = False
    code_focused: bool = False
    temperature_default: float = 0.7


MODEL_REGISTRY: dict[str, ModelInfo] = {
    "gemma3:4b": ModelInfo(
        name="gemma3:4b",
        context_tokens=131072,
        parameters="4.3B",
        quantization="Q4_K_M",
        strengths=["code generation", "instruction following", "vision", "long context", "fast inference"],
        weaknesses=["complex multi-step math", "very deep reasoning chains"],
        best_for=["implement", "review", "ask", "explain", "debug", "compress"],
        pull_command="ollama pull gemma3:4b",
        size_gb=3.3,
        vision=True,
        temperature_default=0.7,
    ),
    "gemma3:12b": ModelInfo(
        name="gemma3:12b",
        context_tokens=131072,
        parameters="12B",
        quantization="Q4_K_M",
        strengths=["stronger reasoning", "better code", "vision", "long context"],
        weaknesses=["slower than 4b", "more RAM required"],
        best_for=["implement", "plan", "review", "research", "complex_debug"],
        pull_command="ollama pull gemma3:12b",
        size_gb=8.1,
        vision=True,
        temperature_default=0.6,
    ),
    "qwen2.5:7b": ModelInfo(
        name="qwen2.5:7b",
        context_tokens=131072,
        parameters="7.6B",
        quantization="Q4_K_M",
        strengths=["code generation", "math", "multilingual", "structured output"],
        weaknesses=["slightly verbose"],
        best_for=["implement", "plan", "math", "structured"],
        pull_command="ollama pull qwen2.5:7b",
        size_gb=4.7,
        code_focused=True,
        temperature_default=0.6,
    ),
    "qwen2.5-coder:7b": ModelInfo(
        name="qwen2.5-coder:7b",
        context_tokens=131072,
        parameters="7.6B",
        quantization="Q4_K_M",
        strengths=["state-of-art code at 7B", "repo-level understanding", "bug fixing"],
        weaknesses=["prose generation weaker"],
        best_for=["implement", "review", "debug", "refactor"],
        pull_command="ollama pull qwen2.5-coder:7b",
        size_gb=4.7,
        code_focused=True,
        temperature_default=0.3,
    ),
    "mistral:7b": ModelInfo(
        name="mistral:7b",
        context_tokens=32768,
        parameters="7.3B",
        quantization="Q4_K_M",
        strengths=["fast", "good for text tasks", "reliable"],
        weaknesses=["smaller context than gemma3", "less code-focused"],
        best_for=["ask", "explain", "summarize", "compress"],
        pull_command="ollama pull mistral:7b",
        size_gb=4.1,
        temperature_default=0.7,
    ),
    "deepseek-r1:7b": ModelInfo(
        name="deepseek-r1:7b",
        context_tokens=131072,
        parameters="7B",
        quantization="Q4_K_M",
        strengths=["chain-of-thought reasoning", "math", "science", "planning"],
        weaknesses=["slower (reasoning tokens)", "verbose"],
        best_for=["plan", "research", "math", "science", "debug"],
        pull_command="ollama pull deepseek-r1:7b",
        size_gb=4.7,
        reasoning=True,
        temperature_default=0.5,
    ),
    "llama3.2:3b": ModelInfo(
        name="llama3.2:3b",
        context_tokens=131072,
        parameters="3.2B",
        quantization="Q4_K_M",
        strengths=["very fast", "small footprint", "good for simple tasks"],
        weaknesses=["weaker at complex code", "less accurate"],
        best_for=["ask", "compress", "explain", "quick"],
        pull_command="ollama pull llama3.2:3b",
        size_gb=2.0,
        temperature_default=0.7,
    ),
    "phi3:mini": ModelInfo(
        name="phi3:mini",
        context_tokens=128000,
        parameters="3.8B",
        quantization="Q4_K_M",
        strengths=["code", "math", "efficient", "long context"],
        weaknesses=["less capable than gemma3:4b overall"],
        best_for=["implement", "math", "quick"],
        pull_command="ollama pull phi3:mini",
        size_gb=2.3,
        code_focused=True,
        temperature_default=0.5,
    ),
}

# Task → ranked list of model preferences
TASK_MODEL_PREFERENCES: dict[str, list[str]] = {
    "implement":    ["qwen2.5-coder:7b", "gemma3:12b", "gemma3:4b", "qwen2.5:7b"],
    "review":       ["qwen2.5-coder:7b", "gemma3:4b", "gemma3:12b"],
    "plan":         ["deepseek-r1:7b", "gemma3:12b", "qwen2.5:7b", "gemma3:4b"],
    "debug":        ["qwen2.5-coder:7b", "deepseek-r1:7b", "gemma3:4b"],
    "research":     ["gemma3:12b", "deepseek-r1:7b", "gemma3:4b"],
    "explain":      ["gemma3:4b", "mistral:7b", "llama3.2:3b"],
    "compress":     ["gemma3:4b", "mistral:7b", "llama3.2:3b"],
    "ask":          ["gemma3:4b", "llama3.2:3b", "mistral:7b"],
    "math":         ["deepseek-r1:7b", "qwen2.5:7b", "phi3:mini"],
    "vision":       ["gemma3:4b", "gemma3:12b"],
}


class ModelRegistry:
    """Static registry for model info and selection."""

    @staticmethod
    def get(name: str) -> Optional[ModelInfo]:
        return MODEL_REGISTRY.get(name)

    @staticmethod
    def all() -> dict[str, ModelInfo]:
        return MODEL_REGISTRY

    @staticmethod
    def select(task_type: str, available: Optional[list[str]] = None) -> str:
        """
        Select the best available model for a task type.
        Falls back down the preference list until finding an available model.
        """
        preferences = TASK_MODEL_PREFERENCES.get(task_type, TASK_MODEL_PREFERENCES["ask"])
        if not available:
            return preferences[0]
        for model in preferences:
            if model in available:
                return model
        return available[0] if available else "gemma3:4b"

    @staticmethod
    def available_models() -> list[str]:
        """Query Ollama for currently installed models."""
        try:
            from openai import OpenAI
            client = OpenAI(base_url="http://localhost:11434/v1", api_key="ollama")
            return [m.id for m in client.models.list().data]
        except Exception:
            return []

    @staticmethod
    def pull_commands(models: Optional[list[str]] = None) -> list[str]:
        targets = models or list(MODEL_REGISTRY.keys())
        return [MODEL_REGISTRY[m].pull_command for m in targets if m in MODEL_REGISTRY]

    @staticmethod
    def print_table() -> None:
        print(f"\n{'Model':<25} {'Params':<8} {'Context':<10} {'Size':<7} {'Best For'}")
        print("-" * 80)
        for name, info in MODEL_REGISTRY.items():
            ctx = f"{info.context_tokens//1000}K"
            best = ", ".join(info.best_for[:3])
            flags = " ".join(f for f, v in [("vision", info.vision), ("reasoning", info.reasoning), ("code", info.code_focused)] if v)
            print(f"{name:<25} {info.parameters:<8} {ctx:<10} {info.size_gb:<7.1f}GB {best}  {flags}")
        print()


if __name__ == "__main__":
    ModelRegistry.print_table()
    print("\nAvailable locally:", ModelRegistry.available_models())
    print("Best for 'implement':", ModelRegistry.select("implement", ModelRegistry.available_models()))
