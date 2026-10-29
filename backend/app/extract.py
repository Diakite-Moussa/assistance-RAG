"""Séance 1 — extraction : PDF -> métadonnées + lignes ordonnées (texte et lignes de tableau)."""
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path

import pdfplumber

MONTHS = {
    "janvier": 1, "fevrier": 2, "mars": 3, "avril": 4, "mai": 5, "juin": 6, "juillet": 7,
    "aout": 8, "septembre": 9, "octobre": 10, "novembre": 11, "decembre": 12,
}
# Un en-tête ou pied de page répété = ligne qui contient « fictif » (cas du corpus EIH).
HEADER_FOOTER = re.compile(r"(H.lianthe.*fictif)|(Document fictif.*page\s+\d+)", re.IGNORECASE)
# Une référence de document, ex. EIH-SRE-GUIDE-2026 (sert à repérer ce qu'une note modifie).
REF_PATTERN = re.compile(r"\b[A-Z]{2,}(?:-[A-Z0-9]+)+\b")


@dataclass
class Line:
    text: str
    page: int
    kind: str  # "text" ou "row" (ligne de tableau reliée à ses en-têtes)


def _norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode()
    return s.lower().strip()


def parse_french_date(label: str) -> str:
    """'1er septembre 2026' -> '2026-09-01' ('' si illisible)."""
    m = re.search(r"(\d{1,2})(?:er)?\s+([a-zéûô]+)\s+(\d{4})", label.lower())
    if not m:
        return ""
    month = MONTHS.get(_norm(m.group(2)))
    return f"{m.group(3)}-{month:02d}-{int(m.group(1)):02d}" if month else ""


def clean(text: str) -> str:
    return text.replace("(cid:127)", "•").replace("\u00a0", " ").strip()


def _read_metadata(first_page) -> tuple[dict, list]:
    """Cherche sur la page 1 le tableau clé/valeur (Référence, Type, Date, Version, Statut)."""
    meta = {"reference": "", "type": "", "date_label": "", "version": "", "status": ""}
    keys = {"reference": "reference", "type de document": "type", "date de publication": "date_label",
            "version": "version", "statut": "status"}
    meta_bboxes = []
    for table in first_page.find_tables():
        rows = [r for r in table.extract() if len(r) == 2 and r[0] and r[1]]
        found = False
        for k, v in rows:
            target = keys.get(_norm(k))
            if target:
                meta[target] = re.sub(r"\s+", " ", v).strip()
                found = True
        if found:
            meta_bboxes.append(table.bbox)
    return meta, meta_bboxes


def _table_to_rows(table_data: list) -> list[str]:
    """Chaque ligne devient 'En-tête : valeur — En-tête : valeur' (lien ligne <-> en-têtes)."""
    headers = [re.sub(r"\s+", " ", c or "").strip() or f"col{i}" for i, c in enumerate(table_data[0])]
    out = []
    for row in table_data[1:]:
        parts = [headers[i] + " : " + " ".join(c.split())
                 for i, c in enumerate(row) if c and c.strip()]
        if parts:
            out.append(clean(" — ".join(parts)))
    return out


def extract_document(pdf_path: Path) -> dict:
    """Retourne {'meta': {...}, 'lines': [Line, ...]} dans l'ordre de lecture du document."""
    with pdfplumber.open(pdf_path) as pdf:
        meta, meta_bboxes = _read_metadata(pdf.pages[0])
        meta["file"] = pdf_path.name
        meta["title"] = (pdf.metadata or {}).get("Title") or pdf_path.stem
        meta["date"] = parse_french_date(meta["date_label"])
        # Un document « modificatif » cite la référence du texte qu'il modifie dans son statut.
        refs = [r for r in REF_PATTERN.findall(meta["status"]) if r != meta["reference"]]
        meta["amends"] = refs[0] if refs and "modifi" in _norm(meta["status"]) else ""

        lines: list[Line] = []
        for page_no, page in enumerate(pdf.pages, start=1):
            skip = list(meta_bboxes) if page_no == 1 else []
            items = []  # (position verticale, Line)
            for table in page.find_tables():
                if any(table.bbox == b for b in skip):
                    continue
                data = table.extract()
                if data and len(data) >= 2:
                    skip.append(table.bbox)
                    for i, row in enumerate(_table_to_rows(data)):
                        items.append((table.bbox[1] + i * 1e-3, Line(row, page_no, "row")))

            def outside(obj, boxes=skip):
                v, h = (obj["top"] + obj["bottom"]) / 2, (obj["x0"] + obj["x1"]) / 2
                return not any(b[0] <= h <= b[2] and b[1] <= v <= b[3] for b in boxes)

            for tl in page.filter(outside).extract_text_lines():
                txt = clean(tl["text"])
                if txt and not HEADER_FOOTER.search(txt):
                    items.append((tl["top"], Line(txt, page_no, "text")))
            lines.extend(line for _, line in sorted(items, key=lambda x: x[0]))
    return {"meta": meta, "lines": lines}


def extract_corpus(corpus_dir: Path) -> list[dict]:
    return [extract_document(p) for p in sorted(corpus_dir.glob("*.pdf"))]