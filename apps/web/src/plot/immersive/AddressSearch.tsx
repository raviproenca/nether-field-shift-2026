// AI-assisted: generated with Claude Code, reviewed by <pending Gabriel>
// Address search (OpenStreetMap Nominatim, no key) limited to Sergipe, plus "use my location".
// Searches run only on submit, one request at a time, as the Nominatim usage policy asks.
import { type FormEvent, useState } from "react";
import type { Lang } from "../i18n";
import type { ImmersiveCopy } from "./copy";

export interface Place {
  lat: number;
  lon: number;
  label: string;
}

interface NominatimResult {
  lat: string;
  lon: string;
  display_name: string;
}

const NOMINATIM_URL = "https://nominatim.openstreetmap.org/search";
const SERGIPE_VIEWBOX = "-38.25,-9.51,-36.39,-11.57"; // west,north,east,south

const shortLabel = (name: string): string => name.split(",").slice(0, 3).join(",").trim();

export default function AddressSearch({ lang, copy, onPick }: { lang: Lang; copy: ImmersiveCopy; onPick: (place: Place) => void }) {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<Place[] | null>(null);
  const [status, setStatus] = useState<"idle" | "searching" | "error" | "locating">("idle");

  async function search(event: FormEvent) {
    event.preventDefault();
    const text = query.trim();
    if (!text || status === "searching") return;
    setStatus("searching");
    const params = new URLSearchParams({
      q: text,
      format: "jsonv2",
      countrycodes: "br",
      viewbox: SERGIPE_VIEWBOX,
      bounded: "1",
      limit: "5",
      "accept-language": lang,
    });
    try {
      const response = await fetch(`${NOMINATIM_URL}?${params}`);
      if (!response.ok) throw new Error(String(response.status));
      const found = (await response.json()) as NominatimResult[];
      const places = found
        .map((item) => ({ lat: Number(item.lat), lon: Number(item.lon), label: shortLabel(item.display_name) }))
        .filter((place, index, all) => all.findIndex((other) => other.label === place.label) === index);
      setResults(places);
      setStatus("idle");
      if (places.length === 1) {
        onPick(places[0]);
        setResults(null);
      }
    } catch {
      setStatus("error");
    }
  }

  function locate() {
    if (!("geolocation" in navigator)) {
      setStatus("error");
      return;
    }
    setStatus("locating");
    navigator.geolocation.getCurrentPosition(
      (position) => {
        setStatus("idle");
        onPick({ lat: position.coords.latitude, lon: position.coords.longitude, label: copy.myLocation });
      },
      () => setStatus("error"),
      { timeout: 10000 },
    );
  }

  return (
    <div className="addr">
      <form className="addr-form" role="search" onSubmit={search}>
        <label className="addr-label" htmlFor="address-input">
          {copy.addressLabel}
        </label>
        <div className="addr-row">
          <input
            id="address-input"
            className="addr-input"
            type="search"
            value={query}
            placeholder={copy.addressPlaceholder}
            autoComplete="street-address"
            onChange={(event) => setQuery(event.target.value)}
          />
          <button type="submit" className="addr-go" disabled={status === "searching"}>
            {status === "searching" ? copy.searching : copy.search}
          </button>
        </div>
      </form>
      <button type="button" className="addr-locate" onClick={locate} disabled={status === "locating"}>
        {status === "locating" ? copy.locating : copy.useMyLocation}
      </button>
      {status === "error" && <p className="addr-message">{copy.searchError}</p>}
      {results !== null && results.length === 0 && <p className="addr-message">{copy.noResults}</p>}
      {results !== null && results.length > 1 && (
        <ul className="addr-results" aria-label={copy.results}>
          {results.map((place) => (
            <li key={`${place.lat},${place.lon}`}>
              <button
                type="button"
                className="addr-result"
                onClick={() => {
                  onPick(place);
                  setResults(null);
                }}
              >
                {place.label}
              </button>
            </li>
          ))}
        </ul>
      )}
      <p className="addr-credit">{copy.searchCredit}</p>
    </div>
  );
}
