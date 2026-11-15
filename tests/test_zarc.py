# AI-assisted: generated with Claude Code, reviewed by Periélio (pending Ravi)
"""ZARC connector with a fake catalog and a fake streamed CSV (no network)."""

import pandas as pd
import pytest
import requests

from src.data import zarc
from src.data.errors import InputError, RemoteDataError

DEC = [f"dec{i}" for i in range(1, 37)]
HEADER = ["Nome_cultura", "SafraIni", "SafraFin", "Cod_Solo", "geocodigo", "UF", "municipio", "Portaria", *DEC]


def csv_row(crop, uf, code, name, decendios):
    return [crop, "2026", "2027", "11", code, uf, name, "Port.1_de_01-01-2026", *map(str, decendios)]


ROWS = [
    csv_row("Milho 1ª Safra", "SE", "2800308", "Aracaju", [0] * 10 + [20, 30, 40] + [0] * 23),
    csv_row("Feijão Caupi", "SE", "2800308", "Aracaju", [0] * 12 + [20] * 5 + [0] * 19),
    csv_row("Soja", "SE", "2800308", "Aracaju", [0] * 36),
    csv_row("Milho 1ª Safra", "BA", "2900108", "Abaíra", [0] * 36),
    csv_row("Milho 1ª Safra", "SE", "2800100", "Amparo do São Francisco", [20] * 36),
]


def csv_bytes(rows=ROWS, header=HEADER):
    text = "\r\n".join(";".join(r) for r in [header, *rows]) + "\r\n"
    return text.encode("utf-8-sig")  # the real files start with a BOM


class FakeResponse:
    def __init__(self, status=200, body=b"", json_body=None):
        self.status_code, self._body, self._json = status, body, json_body

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def iter_lines(self):
        return iter(self._body.split(b"\r\n"))

    def json(self):
        if self._json is None:
            raise ValueError("no json")
        return self._json


CATALOG = {
    "result": {
        "resources": [
            {"name": "Dicionário de Dados - Tábua de Risco", "format": "PDF", "url": "https://x/dict.pdf"},
            {"name": "Tábua de risco - Safra 2025/2026", "format": "CSV", "url": "https://x/2025.csv"},
            {"name": "Tábua de risco - Safra 2026/2027", "format": "CSV", "url": "https://x/2026.csv"},
            {"name": "Tábua de risco - Perene, Olerícola e Sem Safra", "format": "CSV", "url": "https://x/perene.csv"},
        ]
    }
}


class FakeSession:
    """Answers the catalog URL with JSON and any other URL with the CSV bytes."""

    def __init__(self, body=None, status=200, catalog=CATALOG, error=None):
        self.body, self.status, self.catalog, self.error, self.calls = body or csv_bytes(), status, catalog, error, []

    def get(self, url, params=None, stream=False, timeout=None):
        self.calls.append(url)
        if self.error:
            raise self.error
        if url == zarc.CATALOG_URL:
            return FakeResponse(json_body=self.catalog)
        return FakeResponse(self.status, self.body)


def test_list_resources_keeps_only_csv_files():
    names = [r["name"] for r in zarc.list_resources(FakeSession())]
    assert names == [
        "Tábua de risco - Safra 2025/2026",
        "Tábua de risco - Safra 2026/2027",
        "Tábua de risco - Perene, Olerícola e Sem Safra",
    ]


def test_catalog_failures_are_a_clear_error():
    with pytest.raises(RemoteDataError, match="MAPA catalog"):
        zarc.list_resources(FakeSession(error=requests.ConnectionError()))
    with pytest.raises(RemoteDataError, match="MAPA catalog"):
        zarc.list_resources(FakeSession(catalog={"unexpected": 1}))


def test_pick_resource_by_harvest_year_or_perennial():
    resources = zarc.list_resources(FakeSession())
    assert zarc.pick_resource(resources, "2026/2027")["url"] == "https://x/2026.csv"
    assert zarc.pick_resource(resources, "perene")["url"] == "https://x/perene.csv"
    with pytest.raises(InputError, match="available: Tábua de risco - Safra 2025/2026"):
        zarc.pick_resource(resources, "1999/2000")


def test_stream_rows_keeps_one_uf_and_the_wanted_crops():
    frame = zarc.stream_rows("https://x/2026.csv", "SE", ["milho", "FEIJ"], FakeSession())
    assert frame["Nome_cultura"].tolist() == ["Milho 1ª Safra", "Feijão Caupi", "Milho 1ª Safra"]
    assert set(frame["UF"]) == {"SE"} and frame["geocodigo"].iloc[0] == "2800308"
    assert str(frame["dec11"].dtype) == "Int64" and frame["dec11"].iloc[0] == 20


def test_stream_rows_without_crop_filter_keeps_every_crop_of_the_uf():
    assert len(zarc.stream_rows("https://x/2026.csv", "SE", None, FakeSession())) == 4


def test_unexpected_file_or_http_status():
    with pytest.raises(RemoteDataError, match="unexpected format"):
        zarc.stream_rows("https://x", "SE", None, FakeSession(body=csv_bytes([["a", "b"]], ["x", "y"])))
    with pytest.raises(RemoteDataError, match="HTTP 503"):
        zarc.stream_rows("https://x", "SE", None, FakeSession(status=503))
    with pytest.raises(RemoteDataError, match="download from MAPA failed"):
        zarc.stream_rows("https://x", "SE", None, FakeSession(error=requests.Timeout()))


def test_fetch_validates_the_uf_and_reports_empty_results():
    with pytest.raises(InputError, match="unknown UF"):
        zarc.fetch("2026/2027", "XX", session=FakeSession())
    with pytest.raises(InputError, match="no ZARC rows"):
        zarc.fetch("2026/2027", "SE", ["mandioca"], session=FakeSession())


def test_fetch_caches_the_filtered_rows(tmp_path):
    first = FakeSession()
    frame = zarc.fetch("2026/2027", "se", ["milho"], cache_dir=tmp_path, session=first)
    assert len(frame) == 2
    second = FakeSession()
    again = zarc.fetch("2026/2027", "SE", ["milho"], cache_dir=tmp_path, session=second)
    assert zarc.CATALOG_URL in second.calls and "https://x/2026.csv" not in second.calls
    assert again["geocodigo"].tolist() == ["2800308", "2800100"] and len(again) == 2
    zarc.fetch("2026/2027", "SE", ["milho"], cache_dir=tmp_path, refresh=True, session=(third := FakeSession()))
    assert "https://x/2026.csv" in third.calls


def test_cli_writes_csv_and_reports_errors(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(zarc, "fetch", lambda *a, **k: zarc.stream_rows("u", "SE", ["milho"], FakeSession()))
    out = tmp_path / "z.csv"
    assert zarc.main(["--safra", "2026/2027", "--crop", "milho", "--out", str(out)]) == 0
    assert "2 rows" in capsys.readouterr().out and len(pd.read_csv(out)) == 2
    assert zarc.main([]) == 2 and "--safra is required" in capsys.readouterr().err
    assert zarc.main(["--safra", "2026/2027", "--out", str(tmp_path / "z.txt")]) == 2


@pytest.mark.network
def test_real_catalog_lists_the_harvest_files():
    names = [r["name"] for r in zarc.list_resources()]
    assert any("Safra 2026/2027" in n for n in names) and any("Perene" in n for n in names)
