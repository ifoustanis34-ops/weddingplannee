"""Compare the quote templates with the reference images (SSIM by zone) and save the
side-by-side sheets in docs/rendus/diff/ (docs/specs/devis-billets.md §12)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from django.core.management.base import BaseCommand

from documents import fidelity


class Command(BaseCommand):
    help = "SSIM of each zone of the 4 quote designs against devis/*.jpg."

    def add_arguments(self, parser: Any) -> None:
        parser.add_argument("--out", default="")
        parser.add_argument(
            "designs",
            nargs="*",
            default=[*fidelity.REFERENCES, *(f"billet-{v}" for v in fidelity.TICKET_REFERENCES)],
        )

    def handle(self, *args: Any, **options: Any) -> None:
        for design in options["designs"]:
            report = (
                fidelity.compare_ticket(design.removeprefix("billet-"))
                if design.startswith("billet-")
                else fidelity.compare(design)
            )
            scores = "  ".join(
                f"{name} {report.layout[name]:.2f}/{score:.2f}"
                for name, score in report.scores.items()
            )
            self.stdout.write(
                f"{design} · composition min {report.layout_minimum:.3f}"
                f" · glyphes min {report.minimum:.3f} · {scores}"
            )
            if options["out"]:
                path = fidelity.save_diff(report, Path(options["out"]))
                self.stdout.write(f"  → {path}")
