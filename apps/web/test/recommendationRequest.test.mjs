// AI-assisted: generated with Codex, reviewed by Ravi.
import assert from "node:assert/strict";
import test from "node:test";
import {
  demoHistoryMatches,
  postRecommendation,
  recommendationQueryKey,
  toRecommendationRequest,
  RecommendationError,
} from "../src/plot/recommendationRequest.ts";
import { IMMERSIVE_COPY } from "../src/plot/immersive/copy.ts";

const inputs = {
  lat: -10.685,
  lon: -37.425,
  radius_km: 5,
  crop: "maize",
  previousCrop: "beans",
  priority: "water",
  lang: "en",
};

test("request keeps intended crop separate and sends prior crop as history", () => {
  const request = toRecommendationRequest(inputs);
  assert.equal(request.crop, "maize");
  assert.deepEqual(request.previous_crops, ["beans"]);
});

test("unknown prior crop is sent explicitly and cache key includes history", () => {
  const noHistory = toRecommendationRequest({ ...inputs, previousCrop: null });
  const withHistory = toRecommendationRequest(inputs);
  assert.deepEqual(noHistory.previous_crops, []);
  assert.notEqual(recommendationQueryKey(noHistory), recommendationQueryKey(withHistory));
});

test("live request sends JSON and surfaces API failures without a demo substitution", async () => {
  const request = toRecommendationRequest(inputs);
  let sentBody;
  let sentUrl;
  await postRecommendation(
    "https://api.example.test/",
    request,
    undefined,
    async (url, options) => {
      sentUrl = url;
      sentBody = JSON.parse(options.body);
      return Response.json({ recommendation: {}, explanation: "live", lang: "en" });
    },
  );
  assert.equal(sentUrl, "https://api.example.test/recommendation");
  assert.deepEqual(sentBody.previous_crops, ["beans"]);
  assert.equal(sentBody.crop, "maize");

  await assert.rejects(
    postRecommendation(
      "https://api.example.test",
      request,
      undefined,
      async () => Response.json({ error: { message: "service unavailable" } }, { status: 503 }),
    ),
    (error) => error instanceof RecommendationError && error.message === "service unavailable",
  );
});

test("saved demo history is compared with the selected last crop", () => {
  assert.equal(demoHistoryMatches([], null), true);
  assert.equal(demoHistoryMatches([], "beans"), false);
  assert.equal(demoHistoryMatches(["maize", "beans"], "beans"), true);
});

test("saved demo notice discloses when the selected history was not applied", () => {
  const message = IMMERSIVE_COPY.en.savedRun(
    "Itabaiana (Agreste)",
    "2026-11-15",
    "Maize",
    "Save water",
    "Unknown / none",
    "Beans",
    false,
  );
  assert.match(message, /precomputed|saved pilot example/i);
  assert.match(message, /selected last crop \(Beans\) was not applied/i);
});
