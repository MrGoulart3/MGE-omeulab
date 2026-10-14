"""Importa obras públicas de um ORCID informado, preservando a curadoria local.

Usa apenas a biblioteca padrão. Só acessa a API quando executado explicitamente.
Documentação: https://info.orcid.org/documentation/api-tutorials/api-tutorial-read-data-on-a-record/
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys
import unicodedata
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "src/publicacoes.json"


def normalize_orcid(value: str) -> str:
    """Valida formato e dígito verificador ISO 7064 MOD 11-2 do iD."""
    value = value.strip().removeprefix("https://orcid.org/").upper()
    if not re.fullmatch(r"\d{4}-\d{4}-\d{4}-\d{3}[\dX]", value, re.ASCII):
        raise ValueError("Informe um ORCID iD no formato de quatro grupos ou sua URL HTTPS.")
    digits = value.replace("-", "")
    total = 0
    for digit in digits[:-1]:
        total = (total + int(digit)) * 2
    check = (12 - total % 11) % 11
    if digits[-1] != ("X" if check == 10 else str(check)):
        raise ValueError("O dígito verificador do ORCID iD é inválido.")
    return value


def doi_value(summary: dict) -> str:
    """Extrai o primeiro DOI explícito, normalizando prefixos e caixa."""
    identifiers = (summary.get("external-ids") or {}).get("external-id") or []
    for identifier in identifiers:
        if str(identifier.get("external-id-type", "")).lower() != "doi":
            continue
        value = str(identifier.get("external-id-value") or "").strip()
        value = re.sub(r"(?i)^(?:https?://(?:dx\.)?doi\.org/|doi:\s*)", "", value)
        if re.fullmatch(r"10\.\d{4,9}/\S+", value):
            return value.lower()
    return ""


def text_value(parent: dict, key: str) -> str:
    """Lê os campos textuais encapsulados pela API."""
    field = parent.get(key) or {}
    return str(field.get("value") or "").strip()


def publications_from_response(payload: dict) -> list[dict]:
    """Converte resumos de obras, escolhendo a entrada preferida por grupo."""
    if not isinstance(payload, dict) or not isinstance(payload.get("group"), list):
        raise ValueError("Resposta ORCID sem a lista de grupos de obras esperada.")
    result = []
    for group in payload["group"]:
        summaries = group.get("work-summary") or []
        if not isinstance(summaries, list):
            raise ValueError("Grupo de obras inválido na resposta ORCID.")
        if not summaries:
            continue
        summary = max(summaries, key=lambda item: int(item.get("display-index") or 0))
        title = text_value(summary.get("title") or {}, "title")
        if not title:
            continue
        work_type = str(summary.get("type") or "").lower()
        kind = "other"
        if work_type in {"journal-article", "review", "review-article"}:
            kind = "art"
        elif work_type in {"preprint", "working-paper"}:
            kind = "pre"
        elif work_type in {"conference-paper", "conference-abstract", "conference-poster"}:
            kind = "cong"
        year_text = text_value(summary.get("publication-date") or {}, "year")
        item = {
            "y": int(year_text) if year_text.isascii() and year_text.isdigit() else None,
            "k": kind,
            "t": title,
            "a": "",
            "v": text_value(summary, "journal-title"),
        }
        doi = doi_value(summary)
        if doi:
            item["doi"] = doi
        result.append(item)
    return result


def normalized_title(item: dict) -> str:
    """Normaliza títulos apenas para conciliar registros bibliográficos."""
    text = unicodedata.normalize("NFKD", str(item.get("t", "")).casefold())
    return "".join(char for char in text if char.isalnum())


def merge_publications(existing: list[dict], incoming: list[dict]) -> list[dict]:
    """Deduplica por DOI ou título e mantém autores, prêmios e textos curados."""
    result = [dict(item) for item in existing]
    for item in incoming:
        doi = str(item.get("doi") or "").lower()
        title = normalized_title(item)
        previous = None
        for entry in result:
            old_doi = str(entry.get("doi") or "").lower()
            if doi and old_doi:
                matches = doi == old_doi
            else:
                years_match = (
                    not item.get("y") or not entry.get("y")
                    or item["y"] == entry["y"]
                )
                matches = bool(title and title == normalized_title(entry) and years_match)
            if matches:
                previous = entry
                break
        if previous is None:
            result.append(dict(item))
        else:
            for key, value in item.items():
                if not previous.get(key) and value:
                    previous[key] = value
    return sorted(result, key=lambda item: (-(item.get("y") or 0), normalized_title(item)))


def fetch_works(orcid_id: str) -> dict:
    """Lê somente o endpoint público de resumos de obras, com timeout."""
    request = urllib.request.Request(
        f"https://pub.orcid.org/v3.0/{orcid_id}/works",
        headers={"Accept": "application/json", "User-Agent": "omeulab-orcid-sync/1.0"},
    )
    with urllib.request.urlopen(request, timeout=20) as response:
        return json.load(response)


def sync(orcid_id: str, output: Path) -> int:
    """Só substitui o JSON após leitura, conversão e conciliação bem-sucedidas."""
    normalized = normalize_orcid(orcid_id)
    existing = json.loads(output.read_text(encoding="utf-8")) if output.exists() else []
    if not isinstance(existing, list) or any(
        not isinstance(item, dict) or not item.get("t") for item in existing
    ):
        raise ValueError("O arquivo local deve ser uma lista de publicações com título.")
    incoming = publications_from_response(fetch_works(normalized))
    merged = merge_publications(existing, incoming)
    content = json.dumps(merged, ensure_ascii=False, indent=2) + "\n"
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_name(output.name + ".tmp")
    try:
        temporary.write_text(content, encoding="utf-8")
        temporary.replace(output)
    finally:
        temporary.unlink(missing_ok=True)
    return len(merged)


def main() -> int:
    """Executa uma sincronização manual; nunca assume um ORCID do autor."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("orcid_id", help="Seu ORCID iD real; nenhum identificador é presumido.")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    try:
        count = sync(args.orcid_id, args.output)
    except (ValueError, KeyError, TypeError, AttributeError, OSError, urllib.error.URLError) as error:
        print(f"Sincronização não concluída: {error}", file=sys.stderr)
        return 1
    print(f"Arquivo atualizado: {args.output} ({count} publicações). Revise antes do build.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
