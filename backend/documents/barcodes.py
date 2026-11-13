"""Code 128 (subset B) as vector SVG, for the ticket stub (docs/specs/devis-billets.md §2b).

The barcode encodes the readable code of the ticket (`WDV-DG-0001`): the scan app reads it
like the QR. Patterns: widths of bar, space, bar, space, bar, space (11 modules each; the stop
pattern has a seventh bar, 13 modules).
"""

from __future__ import annotations

PATTERNS = [
    "212222",
    "222122",
    "222221",
    "121223",
    "121322",
    "131222",
    "122213",
    "122312",
    "132212",
    "221213",
    "221312",
    "231212",
    "112232",
    "122132",
    "122231",
    "113222",
    "123122",
    "123221",
    "223211",
    "221132",
    "221231",
    "213212",
    "223112",
    "312131",
    "311222",
    "321122",
    "321221",
    "312212",
    "322112",
    "322211",
    "212123",
    "212321",
    "232121",
    "111323",
    "131123",
    "131321",
    "112313",
    "132113",
    "132311",
    "211313",
    "231113",
    "231311",
    "112133",
    "112331",
    "132131",
    "113123",
    "113321",
    "133121",
    "313121",
    "211331",
    "231131",
    "213113",
    "213311",
    "213131",
    "311123",
    "311321",
    "331121",
    "312113",
    "312311",
    "332111",
    "314111",
    "221411",
    "431111",
    "111224",
    "111422",
    "121124",
    "121421",
    "141122",
    "141221",
    "112214",
    "112412",
    "122114",
    "122411",
    "142112",
    "142211",
    "241211",
    "221114",
    "413111",
    "241112",
    "134111",
    "111242",
    "121142",
    "121241",
    "114212",
    "124112",
    "124211",
    "411212",
    "421112",
    "421211",
    "212141",
    "214121",
    "412121",
    "111143",
    "111341",
    "131141",
    "114113",
    "114311",
    "411113",
    "411311",
    "113141",
    "114131",
    "311141",
    "411131",
    "211412",
    "211214",
    "211232",
    "2331112",
]
START_B = 104
STOP = 106
QUIET_MODULES = 10


def encode(text: str) -> list[int]:
    """Symbol values: start B, data, checksum, stop."""
    values = [START_B]
    for char in text:
        code = ord(char) - 32
        if not 0 <= code <= 94:
            raise ValueError(f"Caractère non codable en Code 128 B : {char!r}")
        values.append(code)
    checksum = (START_B + sum(index * value for index, value in enumerate(values[1:], 1))) % 103
    return [*values, checksum, STOP]


def modules(text: str) -> list[int]:
    """Run widths, alternating bar / space, starting with a bar."""
    runs: list[int] = []
    for value in encode(text):
        runs.extend(int(width) for width in PATTERNS[value])
    return runs


def svg(text: str, *, color: str = "#000000", vertical: bool = False) -> str:
    """Bars as rectangles in a viewBox of modules; the template sets the printed size."""
    runs = modules(text)
    total = sum(runs) + 2 * QUIET_MODULES
    x = QUIET_MODULES
    bars = []
    for index, width in enumerate(runs):
        if index % 2 == 0:
            bars.append(
                f'<rect x="0" y="{x}" width="1" height="{width}"/>'
                if vertical
                else f'<rect x="{x}" y="0" width="{width}" height="1"/>'
            )
        x += width
    box = f"0 0 1 {total}" if vertical else f"0 0 {total} 1"
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{box}" preserveAspectRatio="none" '
        f'shape-rendering="crispEdges" fill="{color}">{"".join(bars)}</svg>'
    )
