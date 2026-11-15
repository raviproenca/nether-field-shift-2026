// AI-assisted: generated with Claude Code, reviewed by Periélio (pending human review)
// The two pilots of the demo. Ids match public/data/sergipe/pilots.geojson and public/demo/<id>.json.

export interface DemoPilot {
  id: string;
  label: string;
  lat: number;
  lon: number;
}

export const DEMO_PILOTS: readonly DemoPilot[] = [
  { id: "sergipe_agreste_itabaiana", label: "Itabaiana (Agreste)", lat: -10.685, lon: -37.425 },
  { id: "sergipe_semiarido_ns_gloria", label: "N. S. da Glória (Semiárido)", lat: -10.218, lon: -37.42 },
];
