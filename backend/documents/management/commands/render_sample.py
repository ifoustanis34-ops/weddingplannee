"""Render the reference quote (donnees-exemple.json) to PNG/PDF files, to work on templates."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from django.core.management.base import BaseCommand

from documents import quote_document, rendering, samples


class Command(BaseCommand):
    help = "Render the sample quote with a template (A, B, C, D) and a palette."

    def add_arguments(self, parser: Any) -> None:
        parser.add_argument("--template", default="A", choices=list(quote_document.TEMPLATES))
        parser.add_argument("--palette", default=None)
        parser.add_argument("--lines", type=int, default=0, help="Repeat lines up to N (pages).")
        parser.add_argument("--out", default="/tmp/render")  # noqa: S108 - dev tool

    def handle(self, *args: Any, **options: Any) -> None:
        snapshot = samples.quote_snapshot(options["template"], options["palette"])
        if options["lines"]:
            lines = snapshot["quote"]["lines"]
            snapshot["quote"]["lines"] = [lines[i % len(lines)] for i in range(options["lines"])]
        result = rendering.render(
            quote_document.template_path(snapshot), quote_document.context(snapshot), "sample"
        )
        out = Path(options["out"])
        out.mkdir(parents=True, exist_ok=True)
        stem = f"quote-{options['template']}"
        (out / f"{stem}.pdf").write_bytes(result.pdf)
        for index, page in enumerate(result.pages, start=1):
            (out / f"{stem}-p{index}.png").write_bytes(page)
        self.stdout.write(f"{result.page_count} page(s) → {out}/{stem}*")
