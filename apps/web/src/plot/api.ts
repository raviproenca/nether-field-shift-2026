// AI-assisted: generated with Claude Code, reviewed by Periélio (pending human review)
// The only place the dashboard talks to the outside (AD-1). Without VITE_API_URL it serves a
// real engine output saved in public/demo/, so the screen works before the API is deployed.
import type { Lang } from "./i18n";
import type { RecommendationRequest, RecommendationResponse } from "./types";
import { RecommendationError, postRecommendation } from "./recommendationRequest";

export { RecommendationError } from "./recommendationRequest";

const API_URL = (import.meta.env.VITE_API_URL as string | undefined)?.replace(/\/$/, "") ?? "";

const SAMPLE_PILOT = "sergipe_agreste_itabaiana";

export const USING_SAMPLE = API_URL === "";

export async function fetchRecommendation(
  request: RecommendationRequest,
  signal?: AbortSignal,
): Promise<RecommendationResponse> {
  if (USING_SAMPLE) {
    return fetchDemo(SAMPLE_PILOT, request.lang, signal);
  }
  return postRecommendation(API_URL, request, signal);
}

/** Pre-computed result for a pilot (written by scripts/build_demo_cache.py); no API and no login needed. */
export async function fetchDemo(pilotId: string, lang: Lang, signal?: AbortSignal): Promise<RecommendationResponse> {
  let response: Response;
  try {
    response = await fetch(`${import.meta.env.BASE_URL}demo/${pilotId}${lang === "en" ? "" : `.${lang}`}.json`, { signal });
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

/** Pre-computed result for one pilot, crop and priority (scripts/build_demo_cache.py writes all twelve). */
export async function fetchPilotResult(
  pilotId: string,
  crop: string,
  priority: string,
  lang: Lang,
  signal?: AbortSignal,
): Promise<RecommendationResponse> {
  const suffix = lang === "en" ? "" : `.${lang}`;
  let response: Response;
  try {
    response = await fetch(`${import.meta.env.BASE_URL}demo/${pilotId}/${crop}-${priority}${suffix}.json`, { signal });
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") {
      throw error;
    }
    throw new RecommendationError("The pilot data could not be loaded. Check your connection and try again.");
  }
  if (!response.ok) {
    throw new RecommendationError("The pilot data could not be loaded. Try again in a moment.");
  }
  return (await response.json()) as RecommendationResponse;
}
