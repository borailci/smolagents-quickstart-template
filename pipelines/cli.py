"""Command-line helpers for running knowledge-base and tutorial pipelines."""

from __future__ import annotations

import argparse
from pathlib import Path

from loguru import logger

from pipelines.knowledge_base_builder import KnowledgeBaseBuilder
from pipelines.tutorial_generator import TutorialGenerator


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Utilities for generating knowledge bases and tutorials.",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress non-essential logging output.",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    kb_parser = subparsers.add_parser(
        "knowledge-base",
        help="Generate the knowledge base using sub-agents.",
    )
    kb_parser.add_argument(
        "codebase",
        nargs="?",
        default=None,
        help="Path to the codebase root. Uses CODEBASE_ROOT_PATH if omitted.",
    )
    kb_parser.add_argument(
        "--output",
        dest="output",
        default=None,
        help="Directory where the knowledge base markdown files will be written.",
    )
    kb_parser.add_argument(
        "--sub-agents-root",
        dest="sub_agents_root",
        default=None,
        help="Workspace root where sub-agent artifacts are stored.",
    )

    tutorial_parser = subparsers.add_parser(
        "tutorials",
        help="Generate tutorials using the existing knowledge base.",
    )
    tutorial_parser.add_argument(
        "--codebase",
        dest="codebase",
        default=None,
        help="Path to the codebase root. Uses CODEBASE_ROOT_PATH if omitted.",
    )
    tutorial_parser.add_argument(
        "--knowledge-base",
        dest="knowledge_base",
        default=None,
        help="Directory containing the generated knowledge base files.",
    )
    tutorial_parser.add_argument(
        "--output",
        dest="output",
        default=None,
        help="Directory where tutorial markdown files will be written.",
    )

    return parser.parse_args()


def generate_knowledge_base(
    *,
    codebase: str | Path | None = None,
    output: str | Path | None = None,
    sub_agents_root: str | Path | None = None,
) -> list[Path]:
    builder = KnowledgeBaseBuilder(
        codebase_root=codebase,
        output_root=output,
        sub_agents_root=sub_agents_root,
    )
    return builder.generate()


def generate_tutorials(
    *,
    codebase: str | Path | None = None,
    knowledge_base: str | Path | None = None,
    output: str | Path | None = None,
) -> list[Path]:
    generator = TutorialGenerator(
        codebase_root=codebase,
        knowledge_base_root=knowledge_base,
        output_root=output,
    )
    return generator.generate()


def main() -> None:
    args = parse_args()
    if args.quiet:
        logger.remove()

    if args.command == "knowledge-base":
        outputs = generate_knowledge_base(
            codebase=args.codebase,
            output=args.output,
            sub_agents_root=args.sub_agents_root,
        )
        logger.info("Knowledge base written to %s", outputs)
    elif args.command == "tutorials":
        outputs = generate_tutorials(
            codebase=args.codebase,
            knowledge_base=args.knowledge_base,
            output=args.output,
        )
        logger.info("Tutorials written to %s", outputs)
    else:
        raise ValueError(f"Unknown command: {args.command}")


if __name__ == "__main__":
    main()
