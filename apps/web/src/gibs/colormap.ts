// AI-assisted: generated with Claude Code, reviewed by Ravi
// Reads an official GIBS colormap (colormaps/v1.3/*.xml) into a color scale for the legend.

const TIMEOUT_MS = 15_000;

export interface ColorScale {
  title: string;
  unit: string | null;
  minLabel: string;
  maxLabel: string;
  /** "r,g,b" strings, low to high, from the ColorMapEntry rows that are not transparent. */
  colors: string[];
}

export function parseColormap(xml: string): ColorScale | null {
  const doc = new DOMParser().parseFromString(xml, "text/xml");
  // A file holds several ColorMaps (no data, classes, the data scale); the data scale is the one
  // with a continuous legend. GPM's file has rain then snow; the first one (rain) is used.
  const map = Array.from(doc.getElementsByTagName("ColorMap")).find(
    (candidate) => candidate.querySelector('Legend[type="continuous"]') !== null,
  );
  const legend = map?.querySelector('Legend[type="continuous"]');
  if (!map || !legend) {
    return null;
  }
  const colors = Array.from(map.getElementsByTagName("ColorMapEntry"))
    .filter((entry) => entry.getAttribute("transparent") !== "true")
    .map((entry) => entry.getAttribute("rgb") ?? "")
    .filter((rgb) => rgb !== "");
  if (colors.length === 0) {
    return null;
  }
  return {
    title: map.getAttribute("title") ?? "",
    unit: map.getAttribute("units"),
    minLabel: legend.getAttribute("minLabel") ?? "",
    maxLabel: legend.getAttribute("maxLabel") ?? "",
    colors,
  };
}

const cache = new Map<string, Promise<ColorScale | null>>();

export function fetchColormap(url: string): Promise<ColorScale | null> {
  let pending = cache.get(url);
  if (!pending) {
    pending = fetch(url, { signal: AbortSignal.timeout(TIMEOUT_MS) })
      .then((response) => (response.ok ? response.text() : Promise.reject(new Error(String(response.status)))))
      .then(parseColormap)
      .catch(() => {
        cache.delete(url);
        return null;
      });
    cache.set(url, pending);
  }
  return pending;
}
