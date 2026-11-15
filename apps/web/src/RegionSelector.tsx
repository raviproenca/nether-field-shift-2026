// AI-assisted: generated with Claude Code, reviewed by Ravi
import { REGIONS, type RegionId } from "./regions";

interface RegionSelectorProps {
  value: RegionId;
  onChange: (id: RegionId) => void;
}

export default function RegionSelector({ value, onChange }: RegionSelectorProps) {
  return (
    <fieldset className="segmented">
      <legend className="visually-hidden">Region</legend>
      {REGIONS.map((region) => (
        <label key={region.id} className="segmented-option">
          <input
            type="radio"
            name="region"
            value={region.id}
            checked={region.id === value}
            onChange={() => onChange(region.id)}
          />
          <span>{region.name}</span>
        </label>
      ))}
    </fieldset>
  );
}
