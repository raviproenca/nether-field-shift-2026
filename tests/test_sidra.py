# AI-assisted: generated with Claude Code, reviewed by Periélio (pending Ravi)
"""IBGE SIDRA connector: URL building, parsing, errors and cache, with mocked responses (no network)."""

import json

import numpy as np
import pandas as pd
import pytest
import requests

from src.data import sidra
from src.data.errors import InputError, RemoteDataError

HEADER = {
    "NC": "Nível Territorial (Código)",
    "NN": "Nível Territorial",
    "MC": "Unidade de Medida (Código)",
    "MN": "Unidade de Medida",
    "V": "Valor",
    "D1C": "Município (Código)",
    "D1N": "Município",
    "D2C": "Variável (Código)",
    "D2N": "Variável",
    "D3C": "Ano (Código)",
    "D3N": "Ano",
    "D4C": "Produto das lavouras temporárias e permanentes (Código)",
    "D4N": "Produto das lavouras temporárias e permanentes",
}


def row(value, code="2800100", name="Amparo do São Francisco - SE", product=("40119", "Mandioca"), unit="Hectares"):
    return {
        "NC": "6",
        "NN": "Município",
        "MC": "1006",
        "MN": unit,
        "V": value,
        "D1C": code,
        "D1N": name,
        "D2C": "8331",
        "D2N": "Área plantada ou destinada à colheita",
        "D3C": "2025",
        "D3N": "2025",
        "D4C": product[0],
        "D4N": product[1],
    }


PAYLOAD = [
    HEADER,
    row("39"),
    row("-", "2800209", "Aquidabã - SE"),
    row("X", "2800308", "Aracaju - SE"),
    row("...", "2800407", "Areia Branca - SE"),
]


class FakeResponse:
    def __init__(self, status=200, body=None, text=""):
        self.status_code, self._body, self.text = status, body, text

    def json(self):
        if self._body is None:
            raise ValueError("no json")
        return self._body


class FakeSession:
    def __init__(self, *responses):
        self.responses, self.calls = list(responses), []

    def get(self, url, timeout=None):
        self.calls.append((url, timeout))
        item = self.responses.pop(0)
        if isinstance(item, Exception):
            raise item
        return item


def no_sleep(_seconds):
    pass


def test_build_url_for_all_municipalities_of_sergipe():
    url = sidra.build_url(5457, "8331,216", "last 1", 28, 782, "40112,40119,40122")
    assert (
        url == "https://apisidra.ibge.gov.br/values/t/5457/n6/in%20n3%2028/v/8331,216/p/last%201/c782/40112,40119,40122"
    )


def test_build_url_without_classification_and_with_year_ranges():
    assert sidra.build_url(839, "214", "2020-2025", 28).endswith("/t/839/n6/in%20n3%2028/v/214/p/2020-2025")
    assert sidra.build_url(839, "214", "2020,2023", 28).endswith("/p/2020,2023")


@pytest.mark.parametrize(
    "kwargs",
    [
        {"table": 0},
        {"table": -3},
        {"uf": 5},
        {"uf": 99},
        {"periods": "yesterday"},
        {"periods": "2025-"},
        {"variables": "214;DROP"},
        {"variables": ""},
        {"classification": 782},
        {"categories": "40112"},
        {"classification": 782, "categories": "abc"},
    ],
)
def test_invalid_inputs(kwargs):
    args = {"table": 5457, "variables": "214", "periods": "2025", "uf": 28}
    args.update(kwargs)
    with pytest.raises(InputError):
        sidra.build_url(**args)


def test_parse_response_makes_a_tidy_table_with_symbols():
    frame = sidra.parse_response(PAYLOAD)
    assert list(frame.columns) == [
        "municipio_code",
        "municipio",
        "variavel_code",
        "variavel",
        "ano_code",
        "ano",
        "produto_das_lavouras_temporarias_e_permanentes_code",
        "produto_das_lavouras_temporarias_e_permanentes",
        "unit",
        "value",
        "symbol",
    ]
    assert frame["municipio_code"].tolist() == ["2800100", "2800209", "2800308", "2800407"]
    assert frame["value"].iloc[0] == 39.0
    assert frame["value"].iloc[1] == 0.0 and frame["symbol"].iloc[1] == "-"  # absolute zero
    assert np.isnan(frame["value"].iloc[2]) and frame["symbol"].iloc[2] == "X"  # withheld
    assert np.isnan(frame["value"].iloc[3]) and frame["symbol"].iloc[3] == "..."  # not available
    assert frame["unit"].eq("Hectares").all()


@pytest.mark.parametrize("payload", [[], [HEADER], {"error": "x"}, None, "text"])
def test_empty_or_odd_answers_are_a_clear_error(payload):
    with pytest.raises(RemoteDataError, match="no data"):
        sidra.parse_response(payload)


def test_fetch_calls_the_api_once_and_parses():
    session = FakeSession(FakeResponse(body=PAYLOAD))
    frame = sidra.fetch(5457, "8331", "2025", classification=782, categories="40119", session=session, sleep=no_sleep)
    assert len(frame) == 4 and len(session.calls) == 1
    assert session.calls[0][0].startswith(
        "https://apisidra.ibge.gov.br/values/t/5457/n6/in%20n3%2028/v/8331/p/2025/c782/40119"
    )


def test_value_limit_is_an_input_error():
    body = "Quantidade de valores solicitados: 289328 excedeu o limite: 100000"
    session = FakeSession(FakeResponse(400, text=body))
    with pytest.raises(InputError, match="too many values"):
        sidra.fetch(5457, "214", "all", session=session, sleep=no_sleep)
    assert len(session.calls) == 1


def test_other_api_errors_are_reported_without_retry():
    session = FakeSession(FakeResponse(400, text="Tabela 999999: Tabela inválida"))
    with pytest.raises(RemoteDataError, match="HTTP 400.*Tabela inválida"):
        sidra.fetch(999999, "214", "2025", session=session, sleep=no_sleep)
    assert len(session.calls) == 1


def test_retries_on_timeouts_and_server_errors_then_succeeds():
    session = FakeSession(requests.Timeout(), FakeResponse(503), FakeResponse(body=PAYLOAD))
    assert len(sidra.fetch(5457, "8331", "2025", session=session, sleep=no_sleep)) == 4
    assert len(session.calls) == 3


def test_gives_up_after_retries_and_rejects_invalid_json():
    session = FakeSession(*[requests.ConnectionError() for _ in range(3)])
    with pytest.raises(RemoteDataError, match="unavailable after 3 attempts"):
        sidra.fetch(5457, "8331", "2025", session=session, sleep=no_sleep)
    with pytest.raises(RemoteDataError, match="not valid JSON"):
        sidra.fetch(5457, "8331", "2025", session=FakeSession(FakeResponse(200, None)), sleep=no_sleep)


def test_cache_is_reused_and_a_corrupt_file_is_rebuilt(tmp_path):
    first = FakeSession(FakeResponse(body=PAYLOAD))
    sidra.fetch(5457, "8331", "2025", cache_dir=tmp_path, session=first, sleep=no_sleep)
    second = FakeSession()
    assert len(sidra.fetch(5457, "8331", "2025", cache_dir=tmp_path, session=second, sleep=no_sleep)) == 4
    assert second.calls == []
    (cached,) = tmp_path.glob("*.json")
    cached.write_text("{broken")
    third = FakeSession(FakeResponse(body=PAYLOAD))
    sidra.fetch(5457, "8331", "2025", cache_dir=tmp_path, session=third, sleep=no_sleep)
    assert len(third.calls) == 1 and json.loads(cached.read_text()) == PAYLOAD
    forced = FakeSession(FakeResponse(body=PAYLOAD))
    sidra.fetch(5457, "8331", "2025", cache_dir=tmp_path, refresh=True, session=forced, sleep=no_sleep)
    assert len(forced.calls) == 1


def test_cli_writes_csv(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(sidra, "fetch", lambda *a, **k: sidra.parse_response(PAYLOAD))
    out = tmp_path / "pam.csv"
    argv = [
        "--variable",
        "8331",
        "--period",
        "2025",
        "--classification",
        "782",
        "--categories",
        "40119",
        "--out",
        str(out),
    ]
    assert sidra.main(argv) == 0
    assert "4 values" in capsys.readouterr().out
    assert pd.read_csv(out, dtype={"municipio_code": str}).shape[0] == 4


def test_cli_errors_are_short_messages(tmp_path, capsys):
    assert sidra.main(["--variable", "8331", "--period", "tomorrow", "--out", str(tmp_path / "x.csv")]) == 2
    assert capsys.readouterr().err.startswith("error: invalid period")
    assert sidra.main(["--variable", "8331", "--period", "2025", "--out", str(tmp_path / "x.txt")]) == 2
    assert "unsupported --out" in capsys.readouterr().err


@pytest.mark.network
def test_real_sidra_api_all_municipalities_of_sergipe():
    frame = sidra.fetch(5457, "214", "last 1", classification=782, categories="40119")
    assert len(frame) == 75 and frame["municipio"].str.endswith("- SE").all()
