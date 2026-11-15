// AI-assisted: generated with Claude Code, reviewed by Periélio (pending human review)
// The only place the dashboard talks to the outside (AD-1). Without VITE_API_URL it serves a
// real engine output saved in fixture.json, so the screen works before the API is deployed.
import fixture from "./fixture.json";
import type { ApiErrorBody, RecommendationRequest, RecommendationResponse } from "./types";

const API_URL = (import.meta.env.VITE_API_URL as string | undefined)?.replace(/\/$/, "") ?? "";

export const USING_SAMPLE = API_URL === "";

export class RecommendationError extends Error {}

export async function fetchRecommendation(
  request: RecommendationRequest,
  signal?: AbortSignal,
): Promise<RecommendationResponse> {
  if (USING_SAMPLE) {
    return fixture as RecommendationResponse;
  }
  let response: Response;
  try {
    response = await fetch(`${API_URL}/recommendation`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(request),
      signal,
    });
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") {
      throw error;
    }
    throw new RecommendationError("The analysis service is not reachable. Check your connection and try again.");
  }
  if (!response.ok) {
    const body = (await response.json().catch(() => null)) as ApiErrorBody | null;
    throw new RecommendationError(body?.error.message ?? `The analysis service returned an error (${response.status}).`);
  }
  return (await response.json()) as RecommendationResponse;
}

/** Pre-computed result for a pilot (written by scripts/build_demo_cache.py); no API and no login needed. */
export async function fetchDemo(pilotId: string, signal?: AbortSignal): Promise<RecommendationResponse> {
  let response: Response;
  try {
    response = await fetch(`${import.meta.env.BASE_URL}demo/${pilotId}.json`, { signal });
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") {
      throw error;
    }
    throw new RecommendationError("The demo data could not be loaded. Check your connection and try again.");
  }
  if (!response.ok) {
    throw new RecommendationError("The demo data could not be loaded. Try again in a moment.");
  }
  return (await response.json()) as RecommendationResponse;
}
