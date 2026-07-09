"""Standalone demo module — NOT part of document-intelligence.

Used only to test PR review tooling with a small, unrelated change.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Color:
    name: str
    hex_code: str


PALETTE: tuple[Color, ...] = (
    Color("ocean", "#0077B6"),
    Color("sunset", "#F77F00"),
    Color("forest", "#2D6A4F"),
)


def pick_color(name: str) -> Color | None:
    """Return a palette color by name (case-insensitive)."""
    key = name.strip().lower()
    for color in PALETTE:
        if color.name == key:
            return color
    return None


def format_swatches() -> str:
    """Render palette as simple text swatches for CLI demos."""
    return "\n".join(f"{c.name}: {c.hex_code}" for c in PALETTE)


if __name__ == "__main__":
    print("Sample palette")
    print(format_swatches())
    print("lookup 'ocean' ->", pick_color("ocean"))
