# AI-assisted: generated with Antigravity, reviewed by Lucas Feitosa
"""Catalog of remote sensing and agronomic data sources exposed by the product API."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict


class VariableSpec(BaseModel):
    """Specification of an observable variable provided by a data source."""

    model_config = ConfigDict(extra="forbid")

    name: str
    long_name: str
    unit: str


class AttributionSpec(BaseModel):
    """Attribution metadata, DOI reference, and licensing notice for a source."""

    model_config = ConfigDict(extra="forbid")

    dataset: str
    doi: str | None = None
    url: str
    notice: str | None = None


class SourceSpec(BaseModel):
    """Metadata specification describing a data source available in the toolkit."""

    model_config = ConfigDict(extra="forbid")

    id: str
    name: str
    provider: str
    nasa: bool
    kind: Literal["timeseries", "raster", "static"]
    spatial_resolution: str
    temporal_resolution: str
    latest_date: str | None = None
    requires_login: bool
    variables: list[VariableSpec]
    default_variable: str
    max_radius_km: float
    max_period_days: int
    attribution: AttributionSpec


class SourcesResponse(BaseModel):
    """Envelope response containing the list of filtered or all data sources."""

    model_config = ConfigDict(extra="forbid")

    sources: list[SourceSpec]


class HealthResponse(BaseModel):
    """Health check response schema."""

    model_config = ConfigDict(extra="forbid")

    status: Literal["ok"] = "ok"
    version: str
    time: str


SOURCES_CATALOG: tuple[SourceSpec, ...] = (
    SourceSpec(
        id="power",
        name="NASA POWER",
        provider="NASA Langley Research Center (POWER project)",
        nasa=True,
        kind="timeseries",
        spatial_resolution="0.5° x 0.625° (MERRA-2), 1° (CERES solar)",
        temporal_resolution="daily",
        latest_date="2026-11-11",
        requires_login=False,
        variables=[
            VariableSpec(name="T2M", long_name="Air temperature at 2 m (daily mean)", unit="°C"),
            VariableSpec(name="T2M_MAX", long_name="Air temperature at 2 m (daily maximum)", unit="°C"),
            VariableSpec(name="T2M_MIN", long_name="Air temperature at 2 m (daily minimum)", unit="°C"),
            VariableSpec(name="PRECTOTCORR", long_name="Precipitation (bias-corrected)", unit="mm/day"),
            VariableSpec(
                name="ALLSKY_SFC_SW_DWN",
                long_name="All-sky surface shortwave downward irradiance",
                unit="MJ/m²/day",
            ),
            VariableSpec(name="GWETROOT", long_name="Root zone soil wetness", unit="1 (fraction, 0-1)"),
        ],
        default_variable="T2M",
        max_radius_km=100.0,
        max_period_days=365,
        attribution=AttributionSpec(
            dataset="NASA POWER daily point API (MERRA-2 and CERES SYN1deg), community AG",
            doi=None,
            url="https://power.larc.nasa.gov/",
            notice=None,
        ),
    ),
    SourceSpec(
        id="gldas",
        name="GLDAS Noah land surface model (monthly)",
        provider="NASA GSFC GES DISC",
        nasa=True,
        kind="timeseries",
        spatial_resolution="0.25° (~25 km)",
        temporal_resolution="monthly",
        latest_date="2026-07-31",
        requires_login=True,
        variables=[
            VariableSpec(name="SoilMoi0_10cm_inst", long_name="Soil moisture, 0-10 cm layer", unit="kg/m² (= mm of water)"),
            VariableSpec(name="SoilMoi10_40cm_inst", long_name="Soil moisture, 10-40 cm layer", unit="kg/m² (= mm of water)"),
            VariableSpec(name="Rainf_f_tavg", long_name="Rainfall rate (monthly mean)", unit="mm/day"),
        ],
        default_variable="SoilMoi0_10cm_inst",
        max_radius_km=50.0,
        max_period_days=365,
        attribution=AttributionSpec(
            dataset="GLDAS Noah Land Surface Model L4 monthly 0.25 x 0.25 degree V2.1 (GLDAS_NOAH025_M)",
            doi="10.5067/SXAVCZFAQLNO",
            url="https://disc.gsfc.nasa.gov/datasets/GLDAS_NOAH025_M_2.1/summary",
            notice=None,
        ),
    ),
    SourceSpec(
        id="imerg",
        name="GPM IMERG precipitation (Late run)",
        provider="NASA GSFC GES DISC",
        nasa=True,
        kind="timeseries",
        spatial_resolution="0.1° (~10 km)",
        temporal_resolution="daily",
        latest_date="2026-11-12",
        requires_login=True,
        variables=[
            VariableSpec(name="precipitation", long_name="Daily precipitation (Late run)", unit="mm/day"),
        ],
        default_variable="precipitation",
        max_radius_km=50.0,
        max_period_days=90,
        attribution=AttributionSpec(
            dataset="GPM IMERG Late Precipitation L3 1 day 0.1 degree x 0.1 degree V07 (GPM_3IMERGDL)",
            doi="10.5067/GPM/IMERGDL/DAY/07",
            url="https://disc.gsfc.nasa.gov/datasets/GPM_3IMERGDL_07/summary",
            notice=None,
        ),
    ),
    SourceSpec(
        id="smap",
        name="SMAP enhanced soil moisture (morning pass)",
        provider="NASA NSIDC DAAC",
        nasa=True,
        kind="timeseries",
        spatial_resolution="9 km",
        temporal_resolution="daily (gaps between orbits)",
        latest_date="2026-11-12",
        requires_login=True,
        variables=[
            VariableSpec(name="soil_moisture", long_name="Soil moisture, morning (6 a.m.) overpass", unit="m³/m³"),
        ],
        default_variable="soil_moisture",
        max_radius_km=50.0,
        max_period_days=90,
        attribution=AttributionSpec(
            dataset="SMAP Enhanced L3 Radiometer Global and Polar Grid Daily 9 km EASE-Grid Soil Moisture V006 (SPL3SMP_E)",
            doi="10.5067/M20OXIZHY3RJ",
            url="https://nsidc.org/data/spl3smp_e/versions/6",
            notice=None,
        ),
    ),
    SourceSpec(
        id="modis",
        name="MODIS vegetation index (NDVI)",
        provider="NASA LP DAAC",
        nasa=True,
        kind="raster",
        spatial_resolution="250 m",
        temporal_resolution="16-day composite",
        latest_date="2026-10-16",
        requires_login=True,
        variables=[
            VariableSpec(name="NDVI", long_name="Normalized Difference Vegetation Index", unit="1 (dimensionless, -1 to 1)"),
            VariableSpec(name="EVI", long_name="Enhanced Vegetation Index", unit="1 (dimensionless, -1 to 1)"),
        ],
        default_variable="NDVI",
        max_radius_km=25.0,
        max_period_days=180,
        attribution=AttributionSpec(
            dataset="MODIS/Terra Vegetation Indices 16-Day L3 Global 250m SIN Grid V061 (MOD13Q1)",
            doi="10.5067/MODIS/MOD13Q1.061",
            url="https://lpdaac.usgs.gov/products/mod13q1v061/",
            notice=None,
        ),
    ),
    SourceSpec(
        id="viirs",
        name="VIIRS vegetation index (NDVI)",
        provider="NASA LP DAAC",
        nasa=True,
        kind="raster",
        spatial_resolution="500 m",
        temporal_resolution="16-day composite, one every 16 days",
        latest_date="2026-10-24",
        requires_login=True,
        variables=[
            VariableSpec(name="NDVI", long_name="Normalized Difference Vegetation Index", unit="1 (dimensionless, -1 to 1)"),
            VariableSpec(name="EVI", long_name="Enhanced Vegetation Index", unit="1 (dimensionless, -1 to 1)"),
        ],
        default_variable="NDVI",
        max_radius_km=25.0,
        max_period_days=180,
        attribution=AttributionSpec(
            dataset="VIIRS/NPP Vegetation Indices 16-Day L3 Global 500m SIN Grid V002 (VNP13A1)",
            doi="10.5067/VIIRS/VNP13A1.002",
            url="https://lpdaac.usgs.gov/products/vnp13a1v002/",
            notice=None,
        ),
    ),
    SourceSpec(
        id="hls",
        name="Harmonized Landsat Sentinel-2 (HLS)",
        provider="NASA LP DAAC",
        nasa=True,
        kind="raster",
        spatial_resolution="30 m",
        temporal_resolution="2-3 days",
        latest_date="2026-11-05",
        requires_login=True,
        variables=[
            VariableSpec(name="B02", long_name="Blue band (0.48 µm)", unit="1 (reflectance, 0-1)"),
            VariableSpec(name="B03", long_name="Green band (0.56 µm)", unit="1 (reflectance, 0-1)"),
            VariableSpec(name="B04", long_name="Red band (0.65 µm)", unit="1 (reflectance, 0-1)"),
            VariableSpec(name="B05", long_name="Narrow NIR band (0.86 µm)", unit="1 (reflectance, 0-1)"),
        ],
        default_variable="B04",
        max_radius_km=10.0,
        max_period_days=60,
        attribution=AttributionSpec(
            dataset="Harmonized Landsat Sentinel-2 (HLSL30 / HLSS30) V2.0",
            doi="10.5067/HLS/HLSL30.002",
            url="https://lpdaac.usgs.gov/products/hlsl30v002/",
            notice=None,
        ),
    ),
    SourceSpec(
        id="srtm",
        name="NASADEM terrain (SRTM)",
        provider="NASA JPL NASADEM, served by Microsoft Planetary Computer",
        nasa=True,
        kind="static",
        spatial_resolution="30 m (1 arc-second)",
        temporal_resolution="static (February 2000)",
        latest_date="2000-02-22",
        requires_login=False,
        variables=[
            VariableSpec(name="elevation_m", long_name="Mean elevation inside the terrain radius", unit="m"),
            VariableSpec(name="slope_mean_deg", long_name="Mean slope inside the terrain radius", unit="°"),
            VariableSpec(name="slope_mean_pct", long_name="Mean slope inside the terrain radius", unit="%"),
        ],
        default_variable="elevation_m",
        max_radius_km=10.0,
        max_period_days=0,
        attribution=AttributionSpec(
            dataset="NASADEM Merged DEM Global 1 arc-second V001 (NASADEM_HGT)",
            doi="10.5067/MEASURES/NASADEM/NASADEM_HGT.001",
            url="https://planetarycomputer.microsoft.com/dataset/nasadem",
            notice=None,
        ),
    ),
    SourceSpec(
        id="planetary",
        name="Sentinel-2 L2A (Copernicus)",
        provider="ESA / Copernicus via Microsoft Planetary Computer",
        nasa=False,
        kind="raster",
        spatial_resolution="10 m / 20 m / 60 m",
        temporal_resolution="5 days (2-3 days with both S2A and S2B)",
        latest_date="2026-11-12",
        requires_login=False,
        variables=[
            VariableSpec(name="B02", long_name="Blue band (10 m)", unit="1 (reflectance, 0-1)"),
            VariableSpec(name="B03", long_name="Green band (10 m)", unit="1 (reflectance, 0-1)"),
            VariableSpec(name="B04", long_name="Red band (10 m)", unit="1 (reflectance, 0-1)"),
            VariableSpec(name="B08", long_name="NIR band (10 m)", unit="1 (reflectance, 0-1)"),
        ],
        default_variable="B04",
        max_radius_km=10.0,
        max_period_days=60,
        attribution=AttributionSpec(
            dataset="Sentinel-2 Level-2A BOA Reflectance",
            doi="10.5270/S2_-znk9xsj",
            url="https://planetarycomputer.microsoft.com/dataset/sentinel-2-l2a",
            notice="Contains modified Copernicus Sentinel data. Not NASA data.",
        ),
    ),
)

SOURCES_BY_ID: dict[str, SourceSpec] = {source.id: source for source in SOURCES_CATALOG}
