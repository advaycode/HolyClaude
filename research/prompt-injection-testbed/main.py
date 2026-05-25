from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from anthropic import Anthropic

from agent import SecurityAgent
from attacks import AttackSuite
from data import LOGS
from evaluator import Evaluator, save_report


def build_client() -> Anthropic:
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if api_key:
        return Anthropic(api_key=api_key)
    creds_path = Path.home() / ".claude" / ".credentials.json"
    if creds_path.exists():
        token = json.loads(creds_path.read_text()).get("claudeAiOauth", {}).get("accessToken")
        if token:
            return Anthropic(auth_token=token)
    raise SystemExit("error: set ANTHROPIC_API_KEY or sign in to Claude Code first.")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Adversarial prompt-injection testbed for an LLM log classifier."
    )
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--model", default="claude-haiku-4-5")
    parser.add_argument("--out", type=Path, default=Path("results/results.json"))
    parser.add_argument("--limit", type=int, default=None, help="cap number of logs (smoke tests)")
    parser.add_argument("--quiet", action="store_true", help="suppress per-trial output")
    parser.add_argument("--defense", default="warned", choices=["none", "warned", "spotlight"])
    parser.add_argument("--ablation", action="store_true",
                        help="run all three defenses and print the cross-tab")
    args = parser.parse_args()

    client = build_client()
    suite = AttackSuite()
    logs = LOGS[: args.limit] if args.limit else LOGS
    defenses = ["none", "warned", "spotlight"] if args.ablation else [args.defense]

    print(f"model={args.model} seed={args.seed} n_logs={len(logs)} "
          f"n_attacks={len(suite)} defenses={defenses} "
          f"n_trials={len(logs) * len(suite) * len(defenses)}")

    reports = []
    for d in defenses:
        print("-" * 60 + f"\ndefense={d}\n" + "-" * 60)
        agent = SecurityAgent(client=client, model=args.model, defense=d)
        rep = Evaluator(agent=agent, suite=suite, logs=logs).run(seed=args.seed, verbose=not args.quiet)
        reports.append(rep)
        out_path = args.out.with_stem(f"{args.out.stem}_{d}") if args.ablation else args.out
        save_report(rep, out_path)

    print("-" * 60)
    print(f"{'defense':<10} {'attack':<22} {'CFR':>8} {'DFR':>8}")
    for rep in reports:
        for s in rep.per_attack:
            print(f"{rep.defense:<10} {s.attack:<22} {s.classification_flip_rate:>8.2%} {s.directive_follow_rate:>8.2%}")
    tot_in = sum(r.total_input_tokens for r in reports)
    tot_out = sum(r.total_output_tokens for r in reports)
    print(f"tokens in/out: {tot_in} / {tot_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
