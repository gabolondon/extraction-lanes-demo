"""A one-page example certificate with exactly seven planted identifiers."""

from __future__ import annotations

from pathlib import Path

import pymupdf

PLANTED = [
    "Ingrid Solheim",  # technician name
    "Tobias Wren",  # customer contact name
    "+44 20 7946 0555",  # phone
    "t.wren@example.org",  # email
    "NW-2026-009911",  # certificate number
    "7 Lantern Row",  # site street
    "Port Verity, PV9 8ZZ",  # site city and postcode
]
KEPT = ["2026-05-02", "PG-310"]  # calibration date, instrument model
ROWS = [
    ("Pressure 50 % point reading", "5.01", "bar", "4.98", "5.02"),
    ("Hysteresis reading", "0.04", "%", "0.00", "0.10"),
    ("Supply voltage test point", "24.02", "V", "23.50", "24.50"),
]


def build(path: Path) -> Path:
    doc = pymupdf.open()
    page = doc.new_page()
    y = 60
    page.insert_text((50, y), "Northwind Metrology - Calibration Certificate", fontsize=13)
    lines = [
        f"Certificate No: {PLANTED[4]}",
        f"Technician: {PLANTED[0]}",
        f"Customer contact: {PLANTED[1]}",
        f"Phone: {PLANTED[2]}",
        f"Email: {PLANTED[3]}",
        f"Site address: {PLANTED[5]}",
        f"    {PLANTED[6]}",
        f"Calibration date: {KEPT[0]}",
        f"Instrument model: {KEPT[1]}",
    ]
    for ln in lines:
        y += 18
        page.insert_text((50, y), ln, fontsize=10)
    y += 40
    for name, v, u, lo, hi in ROWS:
        page.insert_text((50, y), name, fontsize=9)
        for x, t in zip((300, 360, 420, 490), (v, u, lo, hi), strict=True):
            page.insert_text((x, y), t, fontsize=9)
        y += 21
    doc.save(str(path))
    return path
