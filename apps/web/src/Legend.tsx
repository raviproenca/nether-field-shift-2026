// AI-assisted: generated with Claude Code, reviewed by Ravi
import { useEffect, useRef, useState } from "react";
import { fetchColormap, type ColorScale } from "./gibs/colormap";
import type { LegendSpec } from "./gibs/layers";

type ScaleState = { status: "loading" } | { status: "error" } | { status: "ready"; scale: ColorScale };

function ColorBar({ colors, label }: { colors: string[]; label: string }) {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const context = canvasRef.current?.getContext("2d");
    if (!context) {
      return;
    }
    colors.forEach((rgb, index) => {
      context.fillStyle = `rgb(${rgb})`;
      context.fillRect(index, 0, 1, 1);
    });
  }, [colors]);

  return <canvas ref={canvasRef} className="legend-bar" width={colors.length} height={1} role="img" aria-label={label} />;
}

function ColormapLegend({ url, unit }: { url: string; unit?: string }) {
  const [state, setState] = useState<ScaleState>({ status: "loading" });

  useEffect(() => {
    let current = true;
    fetchColormap(url).then((scale) => {
      if (current) {
        setState(scale ? { status: "ready", scale } : { status: "error" });
      }
    });
    return () => {
      current = false;
    };
  }, [url]);

  if (state.status === "loading") {
    return <p className="legend-note">Loading the color scale…</p>;
  }
  if (state.status === "error") {
    return (
      <p className="legend-note">
        The color scale couldn't load. <a href={url}>Open the official colormap</a>.
      </p>
    );
  }
  const { scale } = state;
  const shownUnit = scale.unit ?? unit ?? "";
  return (
    <>
      <ColorBar colors={scale.colors} label={`${scale.title} scale from ${scale.minLabel} to ${scale.maxLabel} ${shownUnit}`} />
      <p className="legend-scale num">
        <span>{scale.minLabel}</span>
        <span className="legend-unit">{shownUnit}</span>
        <span>{scale.maxLabel}</span>
      </p>
    </>
  );
}

export default function Legend({ spec }: { spec: LegendSpec }) {
  switch (spec.kind) {
    case "colormap":
      return <ColormapLegend url={spec.url} unit={spec.unit} />;
    case "swatch":
      return (
        <p className="legend-swatch">
          <span className="legend-dot" style={{ background: spec.color }} aria-hidden="true" />
          {spec.label} <span className="legend-unit">({spec.unit})</span>
        </p>
      );
    case "image":
      return <p className="legend-note">{spec.note}</p>;
  }
}
