"""Colour palettes of the documents (docs/specs/devis-billets.md §2c).

Templates only use the ``--doc-*`` variables built here, never a written colour. R4b moves these
palettes to the database (editable by the super-admin) and adds « Couleurs de l’agence ».
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Palette:
    code: str
    name: str
    dark: str  # headers, footer, dark cards
    dark_2: str  # lighter dark, for the gradients of the dark
    accent: str  # gold, silver, blue…
    accent_grad: tuple[str, str, str]  # metallic gradient of the accent (rules, amounts, icons)
    accent_soft: str  # light gold bands
    paper: str
    soft: str  # card backgrounds and alternate rows
    text: str
    muted: str

    def css(self) -> str:
        a, b, c = self.accent_grad
        return (
            f"--doc-dark:{self.dark};--doc-dark-2:{self.dark_2};--doc-accent:{self.accent};"
            f"--doc-accent-1:{a};--doc-accent-2:{b};--doc-accent-3:{c};"
            f"--doc-accent-grad:linear-gradient(100deg,{a} 0%,{b} 50%,{c} 100%);"
            f"--doc-accent-soft:{self.accent_soft};--doc-paper:{self.paper};--doc-soft:{self.soft};"
            f"--doc-text:{self.text};--doc-muted:{self.muted};"
        )


PALETTES: dict[str, Palette] = {
    p.code: p
    for p in (
        Palette(
            "nuit-or",
            "Nuit & Or",
            "#0F1B3D",
            "#1E3146",
            "#C9A24A",
            ("#9C7428", "#F1D48A", "#B88A35"),
            "#F4EEE6",
            "#FBFAF7",
            "#F2F4F7",
            "#0B1C2F",
            "#5B6275",
        ),
        Palette(
            "prune-or",
            "Prune & Or",
            "#3B1E5A",
            "#4C2A6E",
            "#C9A24A",
            ("#9C7428", "#F1D48A", "#B88A35"),
            "#F5EEE6",
            "#FBF9FB",
            "#F4F1F6",
            "#251A38",
            "#665C73",
        ),
        Palette(
            "noir-or",
            "Noir & Or",
            "#121212",
            "#2A2A2A",
            "#C8A048",
            ("#8F6A22", "#F3D57E", "#B98C33"),
            "#F5EFE3",
            "#FBF7EF",
            "#F3F0EC",
            "#141414",
            "#5E5A54",
        ),
        Palette(
            "bleu-royal",
            "Bleu royal",
            "#0E2A5C",
            "#1A3D7A",
            "#3D7BD9",
            ("#2A5FB5", "#9CC2F2", "#3D7BD9"),
            "#E6EFFB",
            "#F7F9FD",
            "#EEF3FA",
            "#0D1E3D",
            "#56637A",
        ),
        Palette(
            "emeraude-or",
            "Émeraude & Or",
            "#0D3B2E",
            "#165043",
            "#C9A24A",
            ("#9C7428", "#F1D48A", "#B88A35"),
            "#F3EEE2",
            "#FBF8F0",
            "#F2F3EE",
            "#0B2A21",
            "#56645E",
        ),
        Palette(
            "bordeaux-or",
            "Bordeaux & Or",
            "#5A1426",
            "#722036",
            "#C9A24A",
            ("#9C7428", "#F1D48A", "#B88A35"),
            "#F6ECE6",
            "#FCF8F6",
            "#F6F0EF",
            "#3A0E19",
            "#6E5A5F",
        ),
        Palette(
            "rose-or",
            "Rose poudré & Or",
            "#7A3B4A",
            "#94505F",
            "#D8B26E",
            ("#A9844A", "#F3DCA6", "#C79E5A"),
            "#F8EEE9",
            "#FDF8F7",
            "#F8F0EF",
            "#4A2530",
            "#79636A",
        ),
        Palette(
            "terracotta-sable",
            "Terracotta & Sable",
            "#6B2E1C",
            "#874029",
            "#D9A066",
            ("#A9733F", "#F2CF9F", "#C98E55"),
            "#F7EDE2",
            "#FCF7F1",
            "#F6EFE7",
            "#431C11",
            "#77655A",
        ),
    )
}
DEFAULT_PALETTE = "nuit-or"


def get(code: str | None) -> Palette:
    return PALETTES.get(code or "", PALETTES[DEFAULT_PALETTE])
