// AI-assisted: generated with Claude Code, reviewed by <pending Gabriel>
// Portuguese for the sentences the engine writes in English. Built from the action codes and the
// numbers already in each sentence; anything not recognised is shown as the engine wrote it.
import type { Lang } from "../i18n";
import type { Action } from "../types";

const numbers = (text: string): string[] => text.match(/-?\d+(?:\.\d+)?/g) ?? [];
const ptNumber = (value: string | undefined): string => (value ?? "").replace(".", ",");
const isoDate = (text: string): string | undefined => text.match(/\d{4}-\d{2}-\d{2}/)?.[0];

export function actionEvidence(action: Action, lang: Lang): string {
  if (lang === "en") return action.evidence;
  const text = action.evidence;
  const [first, second] = numbers(text.replace(/\d{4}-\d{2}-\d{2}/, ""));
  switch (action.code) {
    case "wait_for_window":
      return `O período analisado termina em ${isoDate(text) ?? ""}, fora da janela de plantio do perfil.`;
    case "plant_in_window":
      return `O período analisado termina em ${isoDate(text) ?? ""}, dentro da janela de plantio do perfil.`;
    case "protect_soil":
      return text.includes("NDVI")
        ? `NDVI de ${ptNumber(first)}, no limite de solo exposto (${ptNumber(second)}) ou abaixo.`
        : "Esta estratégia acrescenta cobertura ou uma leguminosa.";
    case "plant_on_contour":
      return `Declividade de ${ptNumber(first)}%, no limite para curva de nível (${ptNumber(second)}%) ou acima.`;
    case "delay_if_dry":
      return `Balanço hídrico de ${ptNumber(first)} mm, no limite de seca severa (${ptNumber(second)} mm) ou abaixo.`;
    default:
      return text;
  }
}

const NOTE_SENTENCES: [RegExp, string][] = [
  [/The forecast is not an observation\./, "A previsão não é uma observação."],
  [/The forecast is absent\./, "A previsão não está disponível."],
  [/Water balance is below the severe deficit threshold\./, "O balanço hídrico está abaixo do limite de seca severa."],
  [/Water balance is missing\./, "Sem dado de balanço hídrico."],
  [/NDVI is missing\./, "Sem dado de NDVI."],
  [/A local technician must confirm this advice\./, "Um técnico local deve confirmar esta recomendação."],
  [/The ZARC check is not done yet\./, "A checagem do ZARC ainda não foi feita."],
  [/The analysis service is not reachable\. Check your connection and try again\./, "O serviço de análise está indisponível. Verifique sua conexão e tente novamente."],
  [/The analysis service returned an error \((\d+)\)\./, "O serviço de análise retornou um erro ($1)."],
  [/current practice/g, "prática atual"],
  [/soil water[_ ]conservation/g, "conservação de solo e água"],
  [/resilient income[_ ]forage/g, "renda resiliente e forragem"],
  [/Plant during the open window\./g, "Plante durante a janela de plantio."],
  [/Wait for the planting window\./g, "Aguarde a janela de plantio."],
  [/Keep the soil covered\./g, "Mantenha o solo coberto."],
  [/Plant on the contour\./g, "Plante em curva de nível."],
  [/Do not plant until the water balance recovers\./g, "Não plante até que o balanço hídrico se recupere."],
  [/ZARC divergence \(MAPA, safra ([\d/]+)\):/, "Divergência do ZARC (MAPA, safra $1):"],
  [/ZARC check \(MAPA, safra ([\d/]+)\): every window is inside the zoning\./, "Checagem do ZARC (MAPA, safra $1): todas as janelas estão dentro do zoneamento."],
  [/Source: (\S+)/, "Fonte: $1"],
  [
    /(\w+): the window (\d{4}-\d{2}-\d{2}) to (\d{4}-\d{2}-\d{2}) is only partly inside the ZARC \((\d+) of (\d+) ten-day periods\)\./g,
    "$1: a janela de $2 a $3 fica só em parte dentro do ZARC ($4 de $5 decêndios).",
  ],
  [/Previous crop history is unknown; pest-cycle break cannot be assessed\./, "O histórico da cultura anterior é desconhecido; não é possível avaliar a quebra do ciclo de pragas."],
  [/Previous botanical family remains in this strategy; a complete pest-cycle break cannot be claimed\./, "A família botânica da cultura anterior permanece nesta estratégia; não é possível afirmar uma quebra completa do ciclo de pragas."],
  [/Introduces (.+), outside (\w+)\./g, "Introduz $1, fora de $2."],
  [/Stays in (\w+); the pest cycle is not broken\./g, "Continua em $1; o ciclo de pragas não é quebrado."],
];

const CROP_PT: Record<string, string> = { maize: "milho", beans: "feijão", cassava: "mandioca" };

export function engineNote(text: string, lang: Lang): string {
  if (lang === "en") return text;
  let result = text;
  for (const [pattern, replacement] of NOTE_SENTENCES) {
    result = result.replace(pattern, replacement);
  }
  result = result.replace(/\b(maize|beans|cassava)(?=:)/g, (crop) => CROP_PT[crop] ?? crop);
  return result;
}
