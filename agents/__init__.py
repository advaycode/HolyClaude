"""HolyClaude agents package."""
from .base_agent import OllamaAgent
from .crawler_agent import CrawlerAgent, BaseSource, SourceRecord, PubMedSource, ArXivSource, GitHubSource, ZenodoSource
from .verifier_agent import VerifierAgent
from .knowledge_writer import KnowledgeWriter
from .prompt_optimizer import PromptOptimizer, PromptPlan, PromptStep
from .research_pipeline import ResearchPipeline, VideoResult, ResearchResult

__all__ = [
    "OllamaAgent",
    "CrawlerAgent", "BaseSource", "SourceRecord",
    "PubMedSource", "ArXivSource", "GitHubSource", "ZenodoSource",
    "VerifierAgent",
    "KnowledgeWriter",
    "PromptOptimizer", "PromptPlan", "PromptStep",
    "ResearchPipeline", "VideoResult", "ResearchResult",
]
