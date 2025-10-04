"""Generate a simple coverage SVG badge from coverage.xml.

Usage:
  python scripts/generate_coverage_badge.py coverage.xml coverage-badge.svg

The SVG style loosely mimics shields.io (flat) but is self-contained so it
can be generated offline in CI without external calls.
"""
from __future__ import annotations

import sys
import xml.etree.ElementTree as ET
from pathlib import Path


def _color(pct: float) -> str:
    if pct >= 95:
        return "#4c1"  # bright green
    if pct >= 90:
        return "#97CA00"
    if pct >= 80:
        return "#a4a61d"
    if pct >= 70:
        return "#dfb317"
    if pct >= 60:
        return "#fe7d37"
    return "#e05d44"  # red


def parse_total_coverage(coverage_xml: Path) -> float:
    tree = ET.parse(coverage_xml)
    root = tree.getroot()
    # coverage.py xml root has 'line-rate'
    line_rate = root.get("line-rate")
    if not line_rate:
        raise RuntimeError("coverage.xml missing line-rate attribute")
    return float(line_rate) * 100.0


def render_badge(pct: float) -> str:
    pct_text = f"{pct:.1f}%" if pct < 100 else "100%"
    label = "coverage"
    # Basic width calculations (approx char width 6 for text)
    label_w = 11 * 6  # 'coverage'
    value_w = len(pct_text) * 6 + 10
    total_w = label_w + value_w
    color = _color(pct)
    return f"""<svg xmlns='http://www.w3.org/2000/svg' width='{total_w}' height='20' role='img' aria-label='{label}: {pct_text}'>
<linearGradient id='smooth' x2='0' y2='100%'>
  <stop offset='0' stop-color='#bbb' stop-opacity='.1' />
  <stop offset='1' stop-opacity='.1' />
</linearGradient>
<mask id='round'>
  <rect width='{total_w}' height='20' rx='3' fill='#fff'/>
</mask>
<g mask='url(#round)'>
  <rect width='{label_w}' height='20' fill='#555'/>
  <rect x='{label_w}' width='{value_w}' height='20' fill='{color}'/>
  <rect width='{total_w}' height='20' fill='url(#smooth)'/>
</g>
<g fill='#fff' text-anchor='middle' font-family='DejaVu Sans,Verdana,Geneva,sans-serif' font-size='11'>
  <text x='{label_w/2}' y='15' fill='#010101' fill-opacity='.3'>{label}</text>
  <text x='{label_w/2}' y='14'>{label}</text>
  <text x='{label_w + value_w/2}' y='15' fill='#010101' fill-opacity='.3'>{pct_text}</text>
  <text x='{label_w + value_w/2}' y='14'>{pct_text}</text>
</g>
</svg>"""


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print("Usage: python scripts/generate_coverage_badge.py coverage.xml coverage-badge.svg", file=sys.stderr)
        return 1
    xml_path = Path(argv[1])
    out_svg = Path(argv[2])
    pct = parse_total_coverage(xml_path)
    svg = render_badge(pct)
    out_svg.write_text(svg)
    print(f"Generated coverage badge {out_svg} for {pct:.2f}%")
    return 0


if __name__ == "__main__":  # pragma: no cover - script entrypoint
    raise SystemExit(main(sys.argv))
