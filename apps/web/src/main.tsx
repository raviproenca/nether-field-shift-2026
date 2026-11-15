// AI-assisted: generated with Claude Code, reviewed by Ravi
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import "@fontsource-variable/geist";
import App from "./App";
import PlotApp from "./plot/PlotApp";
import "./tokens.css";
import "./index.css";

const rootElement = document.getElementById("root");
if (!rootElement) {
  throw new Error("Root element #root not found in index.html");
}

createRoot(rootElement).render(
  <StrictMode>
    {window.location.hash === "#internal" ? <App /> : <PlotApp />}
  </StrictMode>,
);
