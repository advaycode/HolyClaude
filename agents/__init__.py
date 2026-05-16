"""HolyClaude agents package."""
from .base_agent import OllamaAgent
from .crawler_agent import CrawlerAgent, BaseSource, SourceRecord, PubMedSource, ArXivSource, GitHubSource, ZenodoSource
from .verifier_agent import VerifierAgent
from .knowledge_writer import KnowledgeWriter
from .hub_writer import HubWriter
from .prompt_optimizer import PromptOptimizer, PromptPlan, PromptStep
from .research_pipeline import ResearchPipeline, VideoResult, ResearchResult
from .code_agent import CodeAgent
from .diff_agent import DiffAgent
from .study_agent import StudyAgent
from .overnight_agent import OvernightAgent
from .playwright_agent import PlaywrightAgent
from .scholar_agent import ScholarAgent, Scholarship
from .graph_agent import GraphAgent, KnowledgeGraph, GraphNode

__all__ = [
    "OllamaAgent",
    "CrawlerAgent", "BaseSource", "SourceRecord",
    "PubMedSource", "ArXivSource", "GitHubSource", "ZenodoSource",
    "VerifierAgent",
    "KnowledgeWriter",
    "HubWriter",
    "PromptOptimizer", "PromptPlan", "PromptStep",
    "ResearchPipeline", "VideoResult", "ResearchResult",
    "CodeAgent",
    "DiffAgent",
    "StudyAgent",
    "OvernightAgent",
    "PlaywrightAgent",
    "ScholarAgent", "Scholarship",
    "GraphAgent", "KnowledgeGraph", "GraphNode",
]
