// AI-assisted: generated with Claude Code, reviewed by Ravi
// NASA GIBS layers shown on the map.
//
// Every identifier, format, TileMatrixSet and native zoom below was read on 2026-11-14 from the official
// GetCapabilities: https://gibs.earthdata.nasa.gov/wmts/epsg3857/best/1.0.0/WMTSCapabilities.xml
// (Layer > ows:Identifier, Format, TileMatrixSetLink, ResourceURL template). The date ranges are not
// copied here: they change every day, so the app asks GIBS for them at run time (see availability.ts).
// Color scales come from each layer's official colormap (ows:Metadata link in the same document).

const WMTS = "https://gibs.earthdata.nasa.gov/wmts/epsg3857/best";
const WMS = "https://gibs.earthdata.nasa.gov/wms/epsg3857/best/wms.cgi";
const COLORMAPS = "https://gibs.earthdata.nasa.gov/colormaps/v1.3";

export type LayerId = "true-color" | "ndvi" | "lst" | "soil-moisture" | "precipitation" | "fire";

export type LegendSpec =
  | { kind: "colormap"; url: string; unit?: string }
  | { kind: "swatch"; color: string; label: string; unit: string }
  | { kind: "image"; note: string };

export interface GibsLayer {
  id: LayerId;
  name: string;
  /** Satellite or model and compositing period, from GIBS layer metadata (layer-metadata/v1.0/<id>.json). */
  product: string;
  gibsId: string;
  /** Used for the WMTS tiles and for DescribeDomains. */
  tileMatrixSet: string;
  /** MapLibre tile template; {time} is replaced with the selected date (YYYY-MM-DD). */
  tiles: string;
  /** Native zoom of the TileMatrixSet (GoogleMapsCompatible_LevelN = N); MapLibre over-zooms past it. */
  maxZoom: number;
  legend: LegendSpec;
}

function wmtsTiles(gibsId: string, tileMatrixSet: string, extension: "jpeg" | "png"): string {
  // ResourceURL template: {Layer}/default/{Time}/{TileMatrixSet}/{TileMatrix}/{TileRow}/{TileCol}.<ext>
  return `${WMTS}/${gibsId}/default/{time}/${tileMatrixSet}/{z}/{y}/{x}.${extension}`;
}

// Listed bottom to top: the map draws them in this order above the OpenStreetMap base.
export const GIBS_LAYERS: readonly GibsLayer[] = [
  {
    id: "true-color",
    name: "True color",
    product: "VIIRS NOAA-20 corrected reflectance, daily",
    gibsId: "VIIRS_NOAA20_CorrectedReflectance_TrueColor",
    tileMatrixSet: "GoogleMapsCompatible_Level9",
    tiles: wmtsTiles("VIIRS_NOAA20_CorrectedReflectance_TrueColor", "GoogleMapsCompatible_Level9", "jpeg"),
    maxZoom: 9,
    legend: { kind: "image", note: "Natural-color satellite image. It has no color scale or unit." },
  },
  {
    id: "ndvi",
    name: "Vegetation (NDVI)",
    product: "VIIRS NOAA-20, rolling 8-day",
    gibsId: "VIIRS_NOAA20_NDVI_8Day",
    tileMatrixSet: "GoogleMapsCompatible_Level8",
    tiles: wmtsTiles("VIIRS_NOAA20_NDVI_8Day", "GoogleMapsCompatible_Level8", "png"),
    maxZoom: 8,
    // The colormap has no units attribute: NDVI is a ratio without unit.
    legend: { kind: "colormap", url: `${COLORMAPS}/MODIS_NDVI.xml`, unit: "index, no unit" },
  },
  {
    id: "lst",
    name: "Land surface temperature (day)",
    product: "VIIRS NOAA-20, daily",
    gibsId: "VIIRS_NOAA20_Land_Surface_Temp_Day",
    tileMatrixSet: "GoogleMapsCompatible_Level7",
    tiles: wmtsTiles("VIIRS_NOAA20_Land_Surface_Temp_Day", "GoogleMapsCompatible_Level7", "png"),
    maxZoom: 7,
    legend: { kind: "colormap", url: `${COLORMAPS}/MODIS_Land_Surface_Temp.xml` },
  },
  {
    id: "soil-moisture",
    name: "Soil moisture (surface)",
    product: "SMAP L4 model analysis, 9 km, daily 12:00 UTC",
    gibsId: "SMAP_L4_Analyzed_Surface_Soil_Moisture",
    tileMatrixSet: "GoogleMapsCompatible_Level6",
    tiles: wmtsTiles("SMAP_L4_Analyzed_Surface_Soil_Moisture", "GoogleMapsCompatible_Level6", "png"),
    maxZoom: 6,
    legend: { kind: "colormap", url: `${COLORMAPS}/SMAP_Analyzed_Soil_Moisture.xml` },
  },
  {
    id: "precipitation",
    name: "Precipitation rate",
    product: "GPM IMERG, daily",
    gibsId: "IMERG_Precipitation_Rate",
    tileMatrixSet: "GoogleMapsCompatible_Level6",
    tiles: wmtsTiles("IMERG_Precipitation_Rate", "GoogleMapsCompatible_Level6", "png"),
    maxZoom: 6,
    legend: { kind: "colormap", url: `${COLORMAPS}/GPM_Precipitation_Rate.xml` },
  },
  {
    id: "fire",
    name: "Fire hotspots",
    product: "VIIRS NOAA-20 active fires (FIRMS), 375 m, day and night",
    gibsId: "VIIRS_NOAA20_Thermal_Anomalies_375m_All",
    tileMatrixSet: "GoogleMapsCompatible_Level8",
    // This layer is vector-only in the EPSG:3857 WMTS (application/vnd.mapbox-vector-tile), and those
    // tiles answer 404 at every zoom (checked 2026-11-14). The GIBS WMS for EPSG:3857 renders the same
    // layer as PNG (WMS GetCapabilities: wms/epsg3857/best/wms.cgi?SERVICE=WMS&REQUEST=GetCapabilities).
    tiles:
      `${WMS}?SERVICE=WMS&REQUEST=GetMap&VERSION=1.3.0&LAYERS=VIIRS_NOAA20_Thermal_Anomalies_375m_All` +
      "&STYLES=&CRS=EPSG:3857&BBOX={bbox-epsg-3857}&WIDTH=256&HEIGHT=256&FORMAT=image/png&TRANSPARENT=true&TIME={time}",
    maxZoom: 12,
    // Dot color from the official GIBS vector style:
    // https://gibs.earthdata.nasa.gov/vector-styles/v1.0/FIRMS_VIIRS_Thermal_Anomalies.json (circle-color).
    legend: { kind: "swatch", color: "rgb(240, 40, 40)", label: "One active fire detection", unit: "375 m pixel" },
  },
];

export function tilesForDate(layer: GibsLayer, date: string): string {
  return layer.tiles.replace("{time}", date);
}

export function domainsUrl(layer: GibsLayer, start: string, end: string): string {
  // WMTS DescribeDomains (GIBS extension): lists the dates that have imagery between start and end.
  return `${WMTS}/1.0.0/${layer.gibsId}/default/${layer.tileMatrixSet}/all/${start}--${end}.xml`;
}

export const GIBS_CREDIT_URL =
  "https://www.earthdata.nasa.gov/engage/open-data-services-software/earthdata-developer-portal/gibs-api";
