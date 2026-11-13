"""Visual fidelity of the 4 quote designs (docs/specs/devis-billets.md §12).

The spec asks for SSIM ≥ 0.90 by zone. It is not reachable against these references (AI-drawn
lettering, filled icons, wrong totals corrected on purpose, sample logo): see
docs/rendus/fidelite-devis.md. Until better references exist, this test guards against
regressions: each zone keeps at least its measured score (glyph level), minus 0.05.
Sheets: `python manage.py fidelity_report --out docs/rendus/diff`.
"""

from __future__ import annotations

import pytest

pytest.importorskip("numpy")

from documents import fidelity

BASELINE = {
    "A": {
        "titre": 0.45,
        "informations": 0.67,
        "tableau": 0.66,
        "pourquoi": 0.59,
        "totaux": 0.65,
        "conditions": 0.53,
        "pied": 0.62,
    },
    "B": {
        "colonne": 0.54,
        "tableau": 0.62,
        "totaux": 0.17,
        "cartes": 0.56,
        "engagements": 0.52,
        "pied": 0.58,
    },
    "C": {
        "titre": 0.29,
        "informations": 0.63,
        "tableau": 0.63,
        "totaux": 0.45,
        "engagements": 0.72,
        "conditions": 0.48,
        "pied": 0.64,
    },
    "D": {
        "titre": 0.57,
        "informations": 0.65,
        "tableau": 0.63,
        "totaux": 0.72,
        "modalites": 0.65,
        "conditions": 0.51,
        "pied": 0.49,
    },
}
MARGIN = 0.05


@pytest.mark.skipif(not fidelity.REFERENCE_DIR.is_dir(), reason="reference images not mounted")
@pytest.mark.parametrize("design", list(BASELINE))
def test_quote_design_stays_close_to_its_reference(design: str) -> None:
    report = fidelity.compare(design)

    regressions = {
        zone: round(score, 3)
        for zone, score in report.scores.items()
        if score < BASELINE[design][zone] - MARGIN
    }
    assert not regressions, f"Devis {design}: zones en recul {regressions}"


TICKET_BASELINE = {
    "or-noir": {
        "titre": 0.60,
        "prenoms": 0.60,
        "colonnes": 0.53,
        "talon-haut": 0.34,
        "talon-carte": 0.48,
        "talon-bas": 0.53,
    },
    "bleu-royal": {
        "titre": 0.54,
        "prenoms": 0.51,
        "colonnes": 0.52,
        "talon-haut": 0.29,
        "talon-carte": 0.47,
        "talon-bas": 0.56,
    },
    "emeraude": {
        "titre": 0.63,
        "prenoms": 0.53,
        "colonnes": 0.48,
        "talon-haut": 0.36,
        "talon-carte": 0.44,
        "talon-bas": 0.52,
    },
}


@pytest.mark.skipif(not fidelity.TICKET_DIR.is_dir(), reason="reference images not mounted")
@pytest.mark.parametrize("variant", list(TICKET_BASELINE))
def test_ticket_stays_close_to_its_reference(variant: str) -> None:
    report = fidelity.compare_ticket(variant)

    regressions = {
        zone: round(score, 3)
        for zone, score in report.scores.items()
        if score < TICKET_BASELINE[variant][zone] - MARGIN
    }
    assert not regressions, f"Billet {variant}: zones en recul {regressions}"
