// AI-assisted: generated with Codex, reviewed by Ravi.
import assert from "node:assert/strict";
import test from "node:test";
import { engineNote } from "../src/plot/immersive/engineText.ts";

test("Portuguese detail view translates API explanation action, strategy and pest-cycle sentences", () => {
  const apiExplanation = [
    "#1 current practice — rotação: milho; nota: 0.5. Contrapartida: mantém o calendário e a rotina atuais. Ação: Wait for the planting window. Ciclo de pragas: Introduces Poaceae, outside Fabaceae.",
    "#2 soil water_conservation — rotação: milho + feijão; nota: 0.6. Contrapartida: favorece a cobertura e a saúde do solo. Ação: Keep the soil covered. Ciclo de pragas: Previous botanical family remains in this strategy; a complete pest-cycle break cannot be claimed.",
    "#3 resilient income forage — rotação: milho + mandioca; nota: 0.4. Contrapartida: favorece renda. Ação: Wait for the planting window. Ciclo de pragas: Introduces Poaceae, Euphorbiaceae, outside Fabaceae.",
    "Incerteza: The forecast is absent.",
  ].join("\n");

  const localized = engineNote(apiExplanation, "pt-BR");

  assert.match(localized, /#1 prática atual/);
  assert.match(localized, /Ação: Aguarde a janela de plantio\./);
  assert.match(localized, /Ciclo de pragas: Introduz Poaceae, fora de Fabaceae\./);
  assert.match(localized, /#2 conservação de solo e água/);
  assert.match(localized, /Ação: Mantenha o solo coberto\./);
  assert.match(localized, /A família botânica da cultura anterior permanece nesta estratégia/);
  assert.match(localized, /Incerteza: A previsão não está disponível\./);
  assert.match(localized, /#3 renda resiliente e forragem/);
  assert.doesNotMatch(localized, /current practice|Introduces |Previous botanical family remains|Wait for the planting window|The forecast is absent/);
});

test("unknown history note remains explicit in Portuguese while English is unchanged", () => {
  const note = "Previous crop history is unknown; pest-cycle break cannot be assessed.";

  assert.equal(
    engineNote(note, "pt-BR"),
    "O histórico da cultura anterior é desconhecido; não é possível avaliar a quebra do ciclo de pragas.",
  );
  assert.equal(engineNote(note, "en"), note);
});

test("Portuguese live API connection failures are localized and English remains unchanged", () => {
  const error = "The analysis service is not reachable. Check your connection and try again.";

  assert.equal(
    engineNote(error, "pt-BR"),
    "O serviço de análise está indisponível. Verifique sua conexão e tente novamente.",
  );
  assert.equal(engineNote(error, "en"), error);
});
