// AI-assisted: generated with Claude Code, reviewed by Ravi
// Motion for map camera moves. Mirrors --duration-move and --ease-out in tokens.css.

export const MOVE_DURATION_MS = 300;

/** Ease-out quint, close to cubic-bezier(0.22, 1, 0.36, 1). */
export function easeOut(t: number): number {
  return 1 - (1 - t) ** 5;
}

export function prefersReducedMotion(): boolean {
  return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
}
