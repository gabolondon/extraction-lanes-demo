"""Example catalog: 40 parameter codes with English and Spanish aliases.

Fifteen codes come from a quantity x scale-point grid, twenty-five are stand-alone checks.
Everything here is example data.
"""

from __future__ import annotations

from dataclasses import dataclass

NONE_OF_THESE = "none_of_these"


@dataclass(frozen=True)
class Entry:
    code: str
    en: tuple[str, ...]
    es: tuple[str, ...]
    unit: str
    lo: float  # lower tolerance limit
    hi: float  # upper tolerance limit

    @property
    def aliases(self) -> tuple[str, ...]:
        return self.en + self.es


# quantity -> (spanish, unit, full-scale, tolerance)
QUANTITIES = {
    "pressure": ("presión", "bar", 10.0, 0.02),
    "temperature": ("temperatura", "°C", 100.0, 0.15),
    "flow": ("caudal", "L/min", 60.0, 0.30),
}
# point -> (spanish, fraction of full scale)
POINTS = {
    "zero": ("cero", 0.0),
    "25 %": ("25 %", 0.25),
    "50 %": ("50 %", 0.50),
    "75 %": ("75 %", 0.75),
    "full scale": ("fondo de escala", 1.0),
}

# code, english base, spanish base, unit, lo, hi, style (r = "reading", p = "test point")
_STANDALONE = [
    ("HYST", "hysteresis", "histéresis", "%", 0.0, 0.10, "r"),
    ("REPEAT", "repeatability", "repetibilidad", "%", 0.0, 0.05, "r"),
    ("LINEAR", "linearity error", "error de linealidad", "%", 0.0, 0.10, "r"),
    ("DRIFT24", "24 h drift", "deriva a 24 h", "%", 0.0, 0.08, "p"),
    ("RESP", "response time", "tiempo de respuesta", "s", 0.0, 2.0, "r"),
    ("INSRES", "insulation resistance", "resistencia de aislamiento", "MOhm", 100.0, 1000.0, "p"),
    ("AMBT", "ambient temperature", "temperatura ambiente", "°C", 18.0, 28.0, "r"),
    ("AMBH", "ambient humidity", "humedad ambiente", "%RH", 30.0, 70.0, "r"),
    ("SUPV", "supply voltage", "tensión de alimentación", "V", 23.5, 24.5, "p"),
    ("IOUT0", "output current low end", "corriente de salida mínima", "mA", 3.98, 4.02, "p"),
    ("IOUT1", "output current high end", "corriente de salida máxima", "mA", 19.98, 20.02, "p"),
    ("OFFSET", "offset error", "error de desplazamiento", "%", -0.05, 0.05, "r"),
    ("GAIN", "gain error", "error de ganancia", "%", -0.05, 0.05, "r"),
    ("ZSHIFT", "shift after overload", "desvío tras sobrecarga", "%", -0.05, 0.05, "p"),
    ("SPANERR", "span error", "error de alcance", "%", -0.10, 0.10, "r"),
    ("LEAK", "leak rate", "tasa de fuga", "mL/min", 0.0, 0.50, "p"),
    ("STAB", "short-term stability", "estabilidad a corto plazo", "%", 0.0, 0.03, "r"),
    ("NOISE", "output noise", "ruido de salida", "mV", 0.0, 2.0, "r"),
    ("RESOL", "resolution", "resolución", "bar", 0.001, 0.010, "p"),
    ("EXCV", "excitation voltage", "tensión de excitación", "V", 9.9, 10.1, "p"),
    ("BRIDGE", "bridge resistance", "resistencia de puente", "Ohm", 345.0, 355.0, "r"),
    ("OVREC", "overload recovery", "recuperación de sobrecarga", "s", 0.0, 5.0, "p"),
    ("TEMPCO", "thermal coefficient", "coeficiente térmico", "%/K", -0.02, 0.02, "r"),
    ("VIBE", "vibration error", "error por vibración", "%", 0.0, 0.10, "p"),
    ("CABRES", "cable resistance", "resistencia de cable", "Ohm", 0.0, 2.0, "p"),
]


def build_catalog() -> list[Entry]:
    entries: list[Entry] = []
    for q, (q_es, unit, full, tol) in QUANTITIES.items():
        for pt, (pt_es, frac) in POINTS.items():
            nominal = full * frac
            entries.append(
                Entry(
                    code=f"{q[:4].upper()}_{pt.split()[0].upper().replace('%', 'PCT')}"
                    + ("_FS" if pt == "full scale" else ""),
                    en=(f"{q} {pt} point reading",),
                    es=(f"lectura punto {pt_es} {q_es}",),
                    unit=unit,
                    lo=round(nominal - tol, 3),
                    hi=round(nominal + tol, 3),
                )
            )
    for code, en, es, unit, lo, hi, style in _STANDALONE:
        if style == "r":
            en_a, es_a = f"{en} reading", f"lectura de {es}"
        else:
            en_a, es_a = f"{en} test point", f"punto de prueba de {es}"
        entries.append(Entry(code, (en_a,), (es_a,), unit, lo, hi))
    assert len({e.code for e in entries}) == len(entries) == 40
    return entries


CATALOG: list[Entry] = build_catalog()
BY_CODE = {e.code: e for e in CATALOG}

# Names that exist on certificates but are not in the catalog.
OFF_CATALOG = [
    ("warm-up time", "tiempo de calentamiento", "min", 0.0, 30.0),
    ("display brightness check", "control de brillo de pantalla", "%", 50.0, 100.0),
    ("cable length check", "control de longitud de cable", "m", 1.0, 5.0),
    ("firmware build check", "control de versión de firmware", "id", 1.0, 9.0),
]
