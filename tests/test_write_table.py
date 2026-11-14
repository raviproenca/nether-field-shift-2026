# AI-assisted: generated with Claude Code (pending Ravi review)
import pandas as pd

from src.data.cli import write_table


def test_daily_csv_keeps_plain_dates(tmp_path):
    frame = pd.DataFrame({"time": pd.to_datetime(["2025-01-01", "2025-01-02"]), "value": [1.0, 2.0]})
    out = tmp_path / "daily.csv"
    write_table(frame, out)
    assert out.read_text().splitlines()[1:] == ["2025-01-01,1.0", "2025-01-02,2.0"]


def test_subdaily_csv_keeps_the_hour(tmp_path):
    frame = pd.DataFrame({"time": pd.to_datetime(["2025-01-01 00:00", "2025-01-01 03:00"]), "value": [1.0, 2.0]})
    out = tmp_path / "gldas.csv"
    write_table(frame, out)
    assert out.read_text().splitlines()[1:] == ["2025-01-01 00:00,1.0", "2025-01-01 03:00,2.0"]
