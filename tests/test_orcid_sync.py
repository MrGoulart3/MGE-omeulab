"""Testes offline: nenhuma chamada à API ou dado de pessoa real."""

import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock
import urllib.error

SPEC = importlib.util.spec_from_file_location(
    "orcid_sync", Path(__file__).resolve().parents[1] / "scripts/orcid_sync.py"
)
SYNC = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(SYNC)


class OrcidSyncTest(unittest.TestCase):
    def test_rejects_identifier_before_any_request(self) -> None:
        with mock.patch.object(SYNC, "fetch_works") as fetch:
            with self.assertRaises(ValueError):
                SYNC.sync("identificador-a-informar", Path("unused"))
            fetch.assert_not_called()

    def test_group_prefers_display_index_and_normalizes_doi(self) -> None:
        def summary(title: str, index: str) -> dict:
            return {
                "display-index": index, "title": {"title": {"value": title}},
                "type": "journal-article", "publication-date": {"year": {"value": "2025"}},
                "external-ids": {"external-id": [{
                    "external-id-type": "doi", "external-id-value": "https://doi.org/10.1234/TEST"
                }]},
            }
        actual = SYNC.publications_from_response({"group": [{"work-summary": [
            summary("Alternativa", "0"), summary("Preferida", "1")
        ]}]})
        self.assertEqual("Preferida", actual[0]["t"])
        self.assertEqual("10.1234/test", actual[0]["doi"])
        self.assertEqual("", actual[0]["a"])

    def test_sparse_metadata_and_unknown_type(self) -> None:
        result = SYNC.publications_from_response({"group": [{"work-summary": [{
            "title": {"title": {"value": "Obra sem data"}}, "type": "other"
        }]}]})
        self.assertIsNone(result[0]["y"])
        self.assertEqual("other", result[0]["k"])
        self.assertNotIn("doi", result[0])

    def test_merge_preserves_curated_fields_and_removes_duplicate_doi(self) -> None:
        existing = [{"t": "Título curado", "doi": "10.1234/test", "a": "Autoria curada", "aw": "Prêmio", "y": 2025}]
        imported = [{"t": "Título externo", "doi": "10.1234/TEST", "a": "", "y": 2025}]
        result = SYNC.merge_publications(existing, imported + imported)
        self.assertEqual(existing, result)

    def test_title_deduplication_can_add_missing_doi(self) -> None:
        result = SYNC.merge_publications(
            [{"t": "Título: um estudo", "y": 2025, "aw": "Prêmio"}],
            [{"t": "Titulo — um estudo", "y": 2025, "doi": "10.1234/test"}],
        )
        self.assertEqual(1, len(result))
        self.assertEqual("10.1234/test", result[0]["doi"])
        self.assertEqual("Prêmio", result[0]["aw"])

    def test_same_title_with_distinct_doi_or_year_stays_separate(self) -> None:
        entries = [
            {"t": "Mesmo título", "y": 2025, "doi": "10.1234/one"},
            {"t": "Mesmo título", "y": 2025, "doi": "10.1234/two"},
            {"t": "Mesmo título", "y": 2026},
        ]
        self.assertEqual(3, len(SYNC.merge_publications([], entries)))

    def test_failed_response_never_replaces_local_file(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "publicacoes.json"
            output.write_text('[{"t":"Semente"}]\n')
            original = output.read_bytes()
            with mock.patch.object(SYNC, "normalize_orcid", return_value="not-a-real-id"):
                with mock.patch.object(SYNC, "fetch_works", return_value={"error": "bad"}):
                    with self.assertRaises(ValueError):
                        SYNC.sync("not-a-real-id", output)
                with mock.patch.object(SYNC, "fetch_works", side_effect=urllib.error.URLError("offline")):
                    with self.assertRaises(urllib.error.URLError):
                        SYNC.sync("not-a-real-id", output)
            self.assertEqual(original, output.read_bytes())

    def test_success_is_atomic_and_preserves_seed_when_record_is_empty(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "publicacoes.json"
            output.write_text('[{"t":"Semente", "y":2025}]\n')
            with mock.patch.object(SYNC, "normalize_orcid", return_value="not-a-real-id"):
                with mock.patch.object(SYNC, "fetch_works", return_value={"group": []}):
                    self.assertEqual(1, SYNC.sync("not-a-real-id", output))
            self.assertEqual("Semente", json.loads(output.read_text())[0]["t"])
            self.assertFalse(output.with_suffix(".json.tmp").exists())


if __name__ == "__main__":
    unittest.main()
