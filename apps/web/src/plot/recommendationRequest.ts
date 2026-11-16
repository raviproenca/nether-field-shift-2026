// AI-assisted: generated with Codex, reviewed by Ravi.
import type { Crop, Priority, RecommendationRequest, RecommendationResponse } from "./types";

export interface RecommendationInputs {
  lat: number;
  lon: number;
  radius_km: number;
  crop: Crop;
  previousCrop: Crop | null;
  priority: Priority;
  lang: "en" | "pt-BR";
}

export function toRecommendationRequest(inputs: RecommendationInputs) {
  const { previousCrop, ...request } = inputs;
  return { ...request, previous_crops: previousCrop === null ? [] : [previousCrop] };
}

export function recommendationQueryKey(request: {
  lat: number;
  lon: number;
  crop: Crop;
  previous_crops: string[];
  priority: Priority;
  lang: "en" | "pt-BR";
}): string {
  return `${request.lat.toFixed(4)},${request.lon.toFixed(4)}:${request.crop}:${request.previous_crops.join(",")}:${request.priority}:${request.lang}`;
}

export function demoHistoryMatches(savedPreviousCrops: readonly string[] | undefined, selectedPreviousCrop: Crop | null): boolean {
  return (savedPreviousCrops?.at(-1) ?? null) === selectedPreviousCrop;
}

export class RecommendationError extends Error {}

export async function postRecommendation(
  apiUrl: string,
  request: RecommendationRequest,
  signal?: AbortSignal,
  fetcher: typeof fetch = fetch,
): Promise<RecommendationResponse> {
  let response: Response;
  try {
    response = await fetcher(`${apiUrl.replace(/\/$/, "")}/recommendation`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(request),
      signal,
    });
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") throw error;
    throw new RecommendationError("The analysis service is not reachable. Check your connection and try again.");
  }

  if (!response.ok) {
    const body = (await response.json().catch(() => null)) as { error?: { message?: string } } | null;
    throw new RecommendationError(body?.error?.message ?? `The analysis service returned an error (${response.status}).`);
  }
  return (await response.json()) as RecommendationResponse;
}
