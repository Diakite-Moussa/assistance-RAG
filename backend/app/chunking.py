"""Séance 1 — découpage : deux stratégies écrites à la main (pas de LangChain).

Les deux stratégies partent des mêmes lignes annotées (page + section), donc leurs
fragments portent exactement les mêmes métadonnées.
"""
import re
from dataclasses import dataclass

from .extract import Line

# (motif, niveau). Le niveau sert à construire le chemin « Article 9 > 9.1 Absence… ».
HEADINGS = [
    (re.compile(r"^Titre\s+[IVXLC]+\s+[—–-]\s+\S"), 1),
    (re.compile(r"^Article\s+\d+\s+[—–-]\s+\S"), 2),
    (re.compile(r"^\d+\.\s+[A-ZÀ-Ý]"), 1),            # « 2. Les stages »
    (re.compile(r"^\d+\.\d+\s+[A-ZÀ-Ý]"), 2),         # « 2.2 Convention » (3 sous un Article)
    (re.compile(r"^Q\d+\.\s"), 2),                     # « Q4. J'ai été malade… »
]


@dataclass
class AnnotatedLine:
    text: str
    page: int
    kind: str
    section: str
    is_heading: bool


def _heading_level(text: str, stack: list[tuple[int, str]]) -> int | None:
    for pattern, level in HEADINGS:
        if pattern.match(text):
            # Un « 9.1 » placé sous un « Article 9 » est un niveau plus bas.
            if re.match(r"^\d+\.\d+\s", text) and any(t.startswith("Article") for _, t in stack):
                return 3
            return level
    return None


def annotate(lines: list[Line]) -> list[AnnotatedLine]:
    """Ajoute à chaque ligne sa section courante (chemin hiérarchique des titres)."""
    stack: list[tuple[int, str]] = []
    out = []
    for ln in lines:
        level = _heading_level(ln.text, stack) if ln.kind == "text" else None
        if level:
            while stack and stack[-1][0] >= level:
                stack.pop()
            stack.append((level, ln.text.strip()))
        section = " > ".join(t for _, t in stack) or "Préambule"
        out.append(AnnotatedLine(ln.text, ln.page, ln.kind, section, level is not None))
    return out


def _make_chunk(meta: dict, strategy: str, index: int, page: int, section: str, content: str) -> dict:
    return {
        "id": f"{meta['reference']}:{strategy}:{index:03d}",
        "strategy": strategy,
        "file": meta["file"],
        "title": meta["title"],
        "reference": meta["reference"],
        "type": meta["type"],
        "date": meta["date"],
        "version": meta["version"],
        "status": meta["status"],
        "amends": meta["amends"],
        "page": page,
        "section": section,
        "content": content.strip(),
    }


def chunk_structural(doc: dict, max_chars: int = 900) -> list[dict]:
    """Un fragment par section (article, question-réponse, rubrique, bloc de tableau).

    Une section plus longue que max_chars est coupée aux frontières de lignes (une ligne de
    tableau n'est jamais coupée) et son titre est répété en tête de chaque morceau.
    """
    meta, lines = doc["meta"], annotate(doc["lines"])
    groups: list[list[AnnotatedLine]] = []
    for ln in lines:
        if not groups or ln.section != groups[-1][0].section:
            groups.append([])
        groups[-1].append(ln)

    chunks = []
    for group in groups:
        section = group[0].section
        title_line = group[0].text if group[0].is_heading else section.split(" > ")[-1]
        body = [ln for ln in group if not (ln.is_heading and ln is group[0])]
        # un titre seul (ex. « Titre I — Dispositions générales ») n'est pas un fragment utile
        if not body:
            continue
        parts, cur, size = [], [], len(title_line)
        for ln in body:
            if cur and size + len(ln.text) > max_chars:
                parts.append(cur)
                cur, size = [], len(title_line)
            cur.append(ln)
            size += len(ln.text) + 1
        parts.append(cur)
        for part in parts:
            text = title_line + "\n" + "\n".join(ln.text for ln in part)
            chunks.append(_make_chunk(meta, "structural", len(chunks), part[0].page, section, text))
    return [c for c in chunks if len(c["content"]) > 40]


def chunk_fixed(doc: dict, size: int = 500, overlap: int = 100) -> list[dict]:
    """Fenêtre glissante de `size` caractères avec `overlap` de chevauchement.

    On ne coupe pas au milieu d'un mot : la fin de fenêtre recule jusqu'au dernier espace.
    La page et la section d'un fragment sont celles de son premier caractère.
    """
    if overlap >= size:
        raise ValueError("overlap doit être strictement inférieur à size")
    meta, lines = doc["meta"], annotate(doc["lines"])
    text, owners, pos = "", [], 0  # owners : (début de ligne, ligne)
    for ln in lines:
        owners.append((pos, ln))
        text += ln.text + "\n"
        pos += len(ln.text) + 1

    def owner_at(offset: int) -> AnnotatedLine:
        current = owners[0][1]
        for start, ln in owners:
            if start > offset:
                break
            current = ln
        return current

    chunks, start = [], 0
    while start < len(text):
        end = min(start + size, len(text))
        if end < len(text):
            cut = max(text.rfind(" ", start, end), text.rfind("\n", start, end))
            if cut > start + size // 2:
                end = cut
        piece = text[start:end].strip()
        if len(piece) > 40:
            o = owner_at(start)
            chunks.append(_make_chunk(meta, "fixed", len(chunks), o.page, o.section, piece))
        if end >= len(text):
            break
        start = max(end - overlap, start + 1)
    return chunks


def chunk_corpus(docs: list[dict], strategy: str, size: int = 500, overlap: int = 100,
                 max_chars: int = 900) -> list[dict]:
    if strategy == "fixed":
        return [c for d in docs for c in chunk_fixed(d, size, overlap)]
    if strategy == "structural":
        return [c for d in docs for c in chunk_structural(d, max_chars)]
    raise ValueError(f"Stratégie inconnue : {strategy!r} (attendu : 'fixed' ou 'structural')")