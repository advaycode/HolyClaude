"""
study_agent.py — Daily study pipeline (YouTube → NotebookLM → artifact).

Generalized from ap_physics_daily.py. Works for any subject with a topic rotation.

Usage:
    # Built-in subjects:
    agent = StudyAgent.ap_physics()
    agent = StudyAgent.ap_stats()
    agent = StudyAgent.custom(topics=["Topic A", "Topic B"], subject="My Subject")

    # Run daily pipeline (picks today's topic, finds videos, generates artifact):
    result = agent.run_daily(n_videos=4, artifact="video")

    # Force a specific topic:
    result = agent.run_daily(force_topic=3)

    # Dry run (show what would happen without calling NotebookLM):
    result = agent.run_daily(dry_run=True)

    # CLI:
    python agents/study_agent.py --subject ap-physics --artifact video
    python agents/study_agent.py --subject ap-physics --dry-run
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import date
from pathlib import Path
from typing import Optional

from .research_pipeline import search_youtube, VideoResult, NOTEBOOKLM_SCRIPT, _run_notebooklm

# ── built-in topic lists ──────────────────────────────────────────────────────

AP_PHYSICS_TOPICS = [
    "Kinematics 1D motion position velocity acceleration",
    "Kinematics 2D projectile motion",
    "Newton's Laws dynamics net force free body diagram",
    "Friction and applying Newton's Laws",
    "Circular motion centripetal acceleration",
    "Gravitation universal law orbits",
    "Work energy theorem kinetic energy",
    "Conservation of energy potential energy",
    "Power and energy efficiency",
    "Linear momentum impulse",
    "Conservation of momentum collisions",
    "Simple harmonic motion springs pendulum",
    "Torque rotational equilibrium",
    "Rotational kinematics moment of inertia",
    "Electric charge Coulomb's law electric force",
    "DC circuits Ohm's law resistance",
    "Series and parallel circuits Kirchhoff's laws",
    "Mechanical waves properties interference",
    "Sound waves resonance",
    "AP Physics 1 exam multiple choice strategies",
]

AP_STATS_TOPICS = [
    "Exploring Data: distributions, center, spread",
    "Normal distributions and z-scores",
    "Scatterplots, correlation, linear regression",
    "Residuals and regression diagnostics",
    "Two-way tables and conditional distributions",
    "Probability basics: sample space, events, independence",
    "Conditional probability and Bayes",
    "Random variables: discrete and continuous",
    "Binomial distribution",
    "Geometric and Poisson distributions",
    "Sampling distributions for means",
    "Sampling distributions for proportions",
    "Confidence intervals for one proportion",
    "Confidence intervals for one mean (t-interval)",
    "Significance tests: z-test for proportions",
    "Significance tests: t-test for means",
    "Two-sample t-test",
    "Chi-square goodness-of-fit test",
    "Chi-square test for independence",
    "AP Statistics exam free-response strategies",
]

QUALITY_CHANNELS = {
    "ap-physics": ["Khan Academy", "Flipping Physics", "Professor Dave Explains", "APlusPhysics"],
    "ap-stats": ["Khan Academy", "The Organic Chemistry Tutor", "StatQuest with Josh Starmer"],
    "default": ["Khan Academy", "3Blue1Brown", "Crash Course"],
}


def _filter_by_duration(videos: list[VideoResult], min_min: int = 3, max_min: int = 45) -> list[VideoResult]:
    def ok(v: VideoResult) -> bool:
        dur = v.duration or ""
        parts = dur.split(":")
        try:
            if len(parts) == 2:
                total = int(parts[0]) * 60 + int(parts[1])
            elif len(parts) == 3:
                total = int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
            else:
                return True
            return min_min * 60 <= total <= max_min * 60
        except ValueError:
            return True
    return [v for v in videos if ok(v)]


# ── study agent ───────────────────────────────────────────────────────────────

class StudyAgent:
    """
    Daily study pipeline: pick today's topic → find YouTube videos → generate artifact.

    State is persisted in state.json (topic index, last date) so the rotation
    advances one topic per calendar day automatically.
    """

    def __init__(
        self,
        topics: list[str],
        subject: str = "Study",
        quality_channels: Optional[list[str]] = None,
        state_dir: Optional[Path] = None,
        yt_script: Optional[Path] = None,
        nlm_script: Optional[Path] = None,
        artifact_instructions: str = "",
    ) -> None:
        self.topics = topics
        self.subject = subject
        self.quality_channels = quality_channels or QUALITY_CHANNELS.get("default", [])
        self.state_dir = Path(state_dir or Path(__file__).parent.parent / "data" / "study" / subject.replace(" ", "_"))
        self.yt_script = yt_script
        self.nlm_script = nlm_script
        self.artifact_instructions = artifact_instructions or (
            f"Create a high-quality educational artifact covering this {subject} topic. "
            "Include clear explanations, worked examples, and exam-style tips."
        )
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self._state_file = self.state_dir / "state.json"
        self._log_file = self.state_dir / "daily_log.json"

    # ── constructors ──────────────────────────────────────────────────────────

    @classmethod
    def ap_physics(cls, **kw) -> "StudyAgent":
        return cls(
            topics=AP_PHYSICS_TOPICS,
            subject="AP Physics 1",
            quality_channels=QUALITY_CHANNELS["ap-physics"],
            artifact_instructions=(
                "Create a high-quality educational video simulation covering this AP Physics 1 topic. "
                "Include concept explanations, worked problems with step-by-step solutions, "
                "visual diagrams, and exam-style tips for AP Physics 1."
            ),
            **kw,
        )

    @classmethod
    def ap_stats(cls, **kw) -> "StudyAgent":
        return cls(
            topics=AP_STATS_TOPICS,
            subject="AP Statistics",
            quality_channels=QUALITY_CHANNELS["ap-stats"],
            artifact_instructions=(
                "Create a high-quality AP Statistics study guide covering this topic. "
                "Include concept explanations, formula derivations, example problems, and "
                "exam-style free-response tips."
            ),
            **kw,
        )

    @classmethod
    def custom(cls, topics: list[str], subject: str, **kw) -> "StudyAgent":
        return cls(topics=topics, subject=subject, **kw)

    # ── state management ──────────────────────────────────────────────────────

    def _load_state(self) -> dict:
        if self._state_file.exists():
            return json.loads(self._state_file.read_text(encoding="utf-8"))
        return {"last_date": None, "topic_index": 0}

    def _save_state(self, state: dict) -> None:
        self._state_file.write_text(json.dumps(state, indent=2), encoding="utf-8")

    def get_todays_topic(self) -> tuple[int, str]:
        state = self._load_state()
        today = str(date.today())
        if state["last_date"] != today:
            idx = (state["topic_index"] + (1 if state["last_date"] else 0)) % len(self.topics)
            state["last_date"] = today
            state["topic_index"] = idx
            self._save_state(state)
        return state["topic_index"], self.topics[state["topic_index"]]

    def _append_log(self, entry: dict) -> None:
        history: list = []
        if self._log_file.exists():
            try:
                history = json.loads(self._log_file.read_text(encoding="utf-8"))
            except Exception:
                pass
        history.append(entry)
        self._log_file.write_text(json.dumps(history, indent=2), encoding="utf-8")

    # ── pipeline ──────────────────────────────────────────────────────────────

    def find_videos(self, topic: str, n: int = 10) -> list[VideoResult]:
        channels_str = " OR ".join(self.quality_channels)
        query = f"{self.subject} {topic} ({channels_str})"
        print(f"\n[study] YouTube: {query!r}", file=sys.stderr)
        videos = search_youtube(query, n=n, script_path=self.yt_script)
        # Prefer quality channels by boosting their sort score
        quality_set = {ch.lower() for ch in self.quality_channels}
        videos.sort(
            key=lambda v: (any(q in v.channel.lower() for q in quality_set), v.views),
            reverse=True,
        )
        filtered = _filter_by_duration(videos)
        final = (filtered or videos)[:4]
        for v in final:
            print(f"  → {v.channel[:28]:<30} {v.duration:<8} {v.title[:50]}", file=sys.stderr)
        return final

    def send_to_notebooklm(self, topic: str, videos: list[VideoResult], artifact: str) -> dict:
        import tempfile
        notebook_name = f"{self.subject} — {topic[:50]} [{date.today()}]"
        urls = [v.url for v in videos]
        print(f"\n[study] NotebookLM notebook: {notebook_name!r}", file=sys.stderr)

        tmp = self.state_dir / "_tmp_sources.json"
        tmp.write_text(json.dumps(urls), encoding="utf-8")

        try:
            result = _run_notebooklm([
                "pipeline", notebook_name,
                "--sources-file", str(tmp),
                "--artifact", artifact,
                "--instructions", self.artifact_instructions,
            ], self.nlm_script)

            lines = [l for l in result.strip().splitlines() if l.strip()]
            try:
                return json.loads(lines[-1])
            except (json.JSONDecodeError, IndexError):
                return {"raw_output": result}
        finally:
            tmp.unlink(missing_ok=True)

    def run_daily(
        self,
        n_videos: int = 4,
        artifact: str = "video",
        force_topic: Optional[int] = None,
        dry_run: bool = False,
    ) -> dict:
        """Run the full daily study pipeline."""
        if force_topic is not None:
            idx = force_topic % len(self.topics)
            topic = self.topics[idx]
        else:
            idx, topic = self.get_todays_topic()

        print(f"\n{'='*60}", file=sys.stderr)
        print(f"  {self.subject} Daily — {date.today()}", file=sys.stderr)
        print(f"  Topic [{idx+1}/{len(self.topics)}]: {topic}", file=sys.stderr)
        print(f"{'='*60}", file=sys.stderr)

        videos = self.find_videos(topic, n=n_videos)
        if not videos:
            print("[study] No videos found.", file=sys.stderr)
            return {"error": "no videos found", "topic": topic}

        if dry_run:
            print(f"\n[DRY RUN] Would send to NotebookLM ({artifact}):")
            for v in videos:
                print(f"  {v.url}")
            return {"dry_run": True, "topic": topic, "videos": [v.url for v in videos]}

        nlm_result = self.send_to_notebooklm(topic, videos, artifact)
        log_entry = {
            "date": str(date.today()),
            "topic_index": idx,
            "topic": topic,
            "urls": [v.url for v in videos],
            "artifact": artifact,
            "notebooklm": nlm_result,
        }
        self._append_log(log_entry)

        print(f"\n{'='*60}")
        print(f"  Done!  Artifact: {artifact}")
        print(f"  Notebook: {nlm_result.get('notebook_name', 'N/A')}")
        print(f"  ID: {nlm_result.get('notebook_id', 'N/A')}")
        print(f"{'='*60}\n")
        return log_entry


def main() -> None:
    subjects = {"ap-physics": StudyAgent.ap_physics, "ap-stats": StudyAgent.ap_stats}
    parser = argparse.ArgumentParser(description="Daily study pipeline")
    parser.add_argument("--subject", default="ap-physics", choices=list(subjects.keys()))
    parser.add_argument("--artifact", default="video",
                        help="NotebookLM artifact type: video, report, flashcards, slides, mindmap")
    parser.add_argument("--n", type=int, default=4, help="Number of videos")
    parser.add_argument("--force-topic", type=int, default=None)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    agent = subjects[args.subject]()
    agent.run_daily(
        n_videos=args.n,
        artifact=args.artifact,
        force_topic=args.force_topic,
        dry_run=args.dry_run,
    )


if __name__ == "__main__":
    main()
