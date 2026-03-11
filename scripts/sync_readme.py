#!/usr/bin/env python3
"""
Sync auto-generated README sections from CONFIG/*.yaml.
"""

from pathlib import Path
import re
import sys
import yaml


ROOT = Path(__file__).resolve().parents[1]
README = ROOT / "README.md"
CONFIG = ROOT / "CONFIG" / "model_registry.yaml"

START = "<!-- AUTO-GENERATED:execution_profiles:start -->"
END = "<!-- AUTO-GENERATED:execution_profiles:end -->"


def render_execution_profiles_table(config: dict) -> str:
    profiles = config.get("execution_profiles", {})

    lines = [
        "| Profile | 用途 | 说明 | Provider | 推荐模型 |",
        "|---------|------|------|----------|---------|",
    ]

    for name, profile in profiles.items():
        purpose = profile.get("purpose", "")
        description = profile.get("description", "")
        provider = profile.get("provider", "")
        model = profile.get("model", "")
        lines.append(f"| `{name}` | {purpose} | {description} | {provider} | {model} |")

    return "\n".join(lines)


def replace_section(text: str, start: str, end: str, replacement: str) -> str:
    pattern = re.compile(
        re.escape(start) + r".*?" + re.escape(end),
        re.DOTALL
    )
    new_block = f"{start}\n{replacement}\n{end}"
    if not pattern.search(text):
        raise ValueError("README markers not found for execution_profiles section.")
    return pattern.sub(new_block, text)


def main() -> int:
    if not README.exists():
        print(f"README not found: {README}", file=sys.stderr)
        return 1
    if not CONFIG.exists():
        print(f"Config not found: {CONFIG}", file=sys.stderr)
        return 1

    config = yaml.safe_load(CONFIG.read_text(encoding="utf-8")) or {}
    table = render_execution_profiles_table(config)
    readme_text = README.read_text(encoding="utf-8")
    updated = replace_section(readme_text, START, END, table)

    if updated != readme_text:
        README.write_text(updated, encoding="utf-8")
        print("README updated.")
    else:
        print("README already up to date.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
