# AI-assisted: generated with Claude Code, reviewed by Periélio (pending human review)
from src.data.municipality import municipality_code


def test_pilot_points_fall_in_their_municipalities() -> None:
    assert municipality_code(-10.685, -37.425) == "2802908"  # Itabaiana
    assert municipality_code(-10.218, -37.42) == "2804508"  # Nossa Senhora da Glória


def test_point_outside_sergipe_has_no_code() -> None:
    assert municipality_code(-23.5, -46.6) is None


def test_missing_mesh_returns_none(tmp_path) -> None:
    assert municipality_code(-10.685, -37.425, path=tmp_path / "missing.geojson") is None
