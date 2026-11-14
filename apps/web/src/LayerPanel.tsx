// AI-assisted: generated with Claude Code, reviewed by Ravi
import { canShow, hasData, nearestEarlier, type Availability } from "./gibs/availability";
import { formatDate } from "./gibs/dates";
import { GIBS_LAYERS, type LayerId } from "./gibs/layers";
import Legend from "./Legend";

interface LayerPanelProps {
  date: string | null;
  minDate: string;
  maxDate: string;
  onDateChange: (date: string) => void;
  active: ReadonlySet<LayerId>;
  onToggle: (id: LayerId) => void;
  availability: Record<LayerId, Availability>;
  failedTiles: ReadonlySet<LayerId>;
}

/** A sentence when the checkbox alone doesn't tell the whole state; null when it does. */
function layerStatus(on: boolean, date: string | null, availability: Availability): string | null {
  if (availability.status === "loading" || date === null) {
    return "Checking dates…";
  }
  if (availability.status === "error") {
    return on ? "Shown, but couldn't check whether this date has data." : "Couldn't check which dates have data.";
  }
  if (hasData(availability, date)) {
    return null;
  }
  const earlier = nearestEarlier(availability, date);
  const hint = earlier ? `Nearest earlier: ${formatDate(earlier)}.` : `Starts ${formatDate(availability.first)}.`;
  return `No data on ${formatDate(date)}. ${hint}`;
}

export default function LayerPanel({
  date,
  minDate,
  maxDate,
  onDateChange,
  active,
  onToggle,
  availability,
  failedTiles,
}: LayerPanelProps) {
  return (
    <div className="layer-panel">
      <label className="field">
        <span className="field-label">Date (UTC)</span>
        <input
          type="date"
          className="date-input num"
          value={date ?? ""}
          min={minDate}
          max={maxDate}
          disabled={date === null}
          onChange={(event) => event.target.value && onDateChange(event.target.value)}
        />
      </label>
      <fieldset className="layer-list">
        <legend className="field-label">NASA layers</legend>
        {GIBS_LAYERS.map((layer) => {
          const on = active.has(layer.id);
          const layerAvailability = availability[layer.id];
          const shown = on && date !== null && canShow(layerAvailability, date);
          const statusId = `layer-status-${layer.id}`;
          const status = layerStatus(on, date, layerAvailability);
          const tileNote = shown && failedTiles.has(layer.id) ? "Some tiles didn't load." : null;
          const note = [status, tileNote].filter(Boolean).join(" ");
          return (
            <div key={layer.id} className="layer">
              <label className="layer-toggle">
                <input
                  type="checkbox"
                  checked={on}
                  onChange={() => onToggle(layer.id)}
                  aria-describedby={note ? statusId : undefined}
                />
                <span className="layer-name">{layer.name}</span>
              </label>
              {note && (
                <p id={statusId} className="layer-status">
                  {note}
                </p>
              )}
              {shown && (
                <div className="legend">
                  <Legend spec={layer.legend} />
                  <p className="legend-source">{layer.product}</p>
                </div>
              )}
            </div>
          );
        })}
      </fieldset>
    </div>
  );
}
