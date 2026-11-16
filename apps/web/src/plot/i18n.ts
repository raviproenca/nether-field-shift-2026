// AI-assisted: generated with Claude Code, reviewed by Periélio (pending human review)
// All dashboard text in English (default) and Brazilian Portuguese. Engine text that comes from the
// API (evidence lines, uncertainty and validation notes) stays as the engine wrote it.

export type Lang = "en" | "pt-BR";
export const DEFAULT_LANG: Lang = "en";

export interface Copy {
  title: string;
  intro: string;
  quickDemo: string;
  demoGroup: string;
  crop: string;
  priority: string;
  selectedPoint: string;
  sampleNotice: string;
  savedExample: (place: string, date: string, forThisPoint: boolean) => string;
  mapLabel: string;
  tilesProblem: string;
  webglProblem: string;
  noPlot: string;
  analysing: string;
  genericError: string;
  score: string;
  scoreBasis: string;
  cropHistory: (lastCrop: string, intendedCrop: string) => string;
  noPreviousCrop: string;
  strategiesHeading: string;
  evidenceHeading: string;
  summary: string;
  tradeOffs: string;
  plantingDates: string;
  whatToDo: string;
  toHarvest: (days: number) => string;
  pestBroken: string;
  pestNotBroken: string;
  pestNotAssessed: string;
  waterDemand: string;
  to: string;
  noData: string;
  derivedBySystem: string;
  measure: string;
  value: string;
  source: string;
  observedLabel: string;
  forecastLabel: string;
  forecastMissing: string;
  chartRain: string;
  chartEt0: string;
  chartBalance: string;
  chartDemand: string;
  chartDemandCaption: string;
  chartCaption: (observed: string, forecast: string | null) => string;
  diagnosisTable: string;
  projectionTable: string;
  languageButton: string;
  languageButtonLabel: string;
  units: { mm: string; mmDay: string; days: string };
  crops: Record<string, string>;
  priorities: Record<string, string>;
  tradeOffLabels: Record<string, string>;
  strategyTitles: Record<string, string>;
  actions: Record<string, string>;
  metrics: Record<string, string>;
}

const EN: Copy = {
  title: "Field Shift: planting decision",
  intro: "Click a point on the map, choose a crop and a priority, and compare three strategies.",
  quickDemo: "Quick demo:",
  demoGroup: "Demo pilots",
  crop: "Crop",
  priority: "Priority",
  selectedPoint: "Selected point",
  sampleNotice:
    "Sample result: no analysis service is configured, so this shows one saved engine run (Itabaiana, maize) for any point.",
  savedExample: (place, date, forThisPoint) =>
    forThisPoint
      ? `Saved example: this result was computed on ${date} for ${place}, not for the point you clicked. Crop and priority do not change it.`
      : `Saved result for ${place}, computed on ${date}.`,
  mapLabel: "Map of Sergipe. Click to choose the plot.",
  tilesProblem: "Map tiles couldn't load. Check your connection, then reload.",
  webglProblem: "This browser can't draw the map.",
  noPlot: "No plot selected yet.",
  analysing: "Analysing the plot…",
  genericError: "Something went wrong. Try again.",
  score: "Rule score",
  scoreBasis: "This is a rule-based comparison for the selected priority, not a yield probability.",
  cropHistory: (lastCrop, intendedCrop) => `Last crop grown: ${lastCrop}. Intended crop: ${intendedCrop}.`,
  noPreviousCrop: "unknown / none",
  strategiesHeading: "Three strategies, side by side",
  evidenceHeading: "Evidence",
  summary: "Summary",
  tradeOffs: "Trade-offs",
  plantingDates: "Planting dates",
  whatToDo: "What to do",
  toHarvest: (days) => `${days} days to harvest`,
  pestBroken: "Breaks the pest cycle",
  pestNotBroken: "Does not break the pest cycle",
  pestNotAssessed: "Pest-cycle break cannot be assessed without crop history.",
  waterDemand: "Water demand",
  to: "to",
  noData: "No data",
  derivedBySystem: "Derived by the engine",
  measure: "Measure",
  value: "Value",
  source: "Source",
  observedLabel: "Observed",
  forecastLabel: "Forecast",
  forecastMissing: "The 15-day forecast is not available right now.",
  chartRain: "Rain per day",
  chartEt0: "Reference evapotranspiration (ET0) per day",
  chartBalance: "Water balance",
  chartDemand: "Water demand over the cycle, by strategy",
  chartDemandCaption: "Crop profile water need summed over the planting schedule.",
  chartCaption: (observed, forecast) => `Observed: ${observed}.${forecast ? ` Forecast: ${forecast}.` : ""}`,
  diagnosisTable: "Diagnosis: what satellites observed",
  projectionTable: "Projection: next 15 days",
  languageButton: "PT-BR",
  languageButtonLabel: "Mudar para português (Brasil)",
  units: { mm: "mm", mmDay: "mm/day", days: "days" },
  crops: { maize: "Maize", beans: "Beans", cassava: "Cassava" },
  priorities: { water: "Save water", soil: "Protect soil", erosion: "Control erosion", income: "Income" },
  tradeOffLabels: {
    keeps_current_calendar: "Keeps the current calendar and routine",
    favors_cover_and_soil: "Favors soil cover and soil health",
    favors_forage_or_income: "Favors forage and income",
  },
  strategyTitles: {
    current_practice: "Current practice",
    soil_water_conservation: "Soil and water conservation",
    resilient_income_forage: "Resilient income and forage",
  },
  actions: {},
  metrics: {
    rain_total: "Rain in the period",
    forecast_rain_total: "Forecast rain",
    rain_daily: "Mean daily rain",
    et0_daily: "Mean daily ET0",
    water_balance: "Water balance",
    soil_moisture: "Surface soil moisture",
    temperature_mean: "Mean temperature",
    temperature_max: "Maximum temperature",
    ndvi: "Vegetation index (NDVI)",
    elevation: "Elevation",
    slope: "Mean slope",
  },
};

const PT: Copy = {
  title: "Field Shift: decisão de plantio",
  intro: "Clique em um ponto no mapa, escolha a cultura e a prioridade e compare três estratégias.",
  quickDemo: "Demonstração rápida:",
  demoGroup: "Pilotos da demonstração",
  crop: "Cultura",
  priority: "Prioridade",
  selectedPoint: "Ponto selecionado",
  sampleNotice:
    "Resultado de exemplo: nenhum serviço de análise está configurado, então aparece uma execução salva do motor (Itabaiana, milho) para qualquer ponto.",
  savedExample: (place, date, forThisPoint) =>
    forThisPoint
      ? `Exemplo salvo: este resultado foi calculado em ${date} para ${place}, não para o ponto clicado. Cultura e prioridade não o alteram.`
      : `Resultado salvo para ${place}, calculado em ${date}.`,
  mapLabel: "Mapa de Sergipe. Clique para escolher o talhão.",
  tilesProblem: "Não foi possível carregar o mapa. Verifique a conexão e recarregue a página.",
  webglProblem: "Este navegador não consegue desenhar o mapa.",
  noPlot: "Nenhum talhão selecionado ainda.",
  analysing: "Analisando o talhão…",
  genericError: "Algo deu errado. Tente novamente.",
  score: "Nota baseada em regras",
  scoreBasis: "É uma comparação baseada em regras para a prioridade escolhida, não uma probabilidade de rendimento.",
  cropHistory: (lastCrop, intendedCrop) => `Última cultura cultivada: ${lastCrop}. Cultura pretendida: ${intendedCrop}.`,
  noPreviousCrop: "não informada",
  strategiesHeading: "Três estratégias, lado a lado",
  evidenceHeading: "Evidências",
  summary: "Resumo",
  tradeOffs: "Prós e contras",
  plantingDates: "Datas de plantio",
  whatToDo: "O que fazer",
  toHarvest: (days) => `${days} dias até a colheita`,
  pestBroken: "Quebra o ciclo de pragas",
  pestNotBroken: "Não quebra o ciclo de pragas",
  pestNotAssessed: "Não é possível avaliar a quebra do ciclo de pragas sem o histórico da cultura anterior.",
  waterDemand: "Demanda de água",
  to: "a",
  noData: "Sem dados",
  derivedBySystem: "Calculado pelo motor",
  measure: "Medida",
  value: "Valor",
  source: "Fonte",
  observedLabel: "Observado",
  forecastLabel: "Previsão",
  forecastMissing: "A previsão de 15 dias não está disponível agora.",
  chartRain: "Chuva por dia",
  chartEt0: "Evapotranspiração de referência (ET0) por dia",
  chartBalance: "Balanço hídrico",
  chartDemand: "Demanda de água no ciclo, por estratégia",
  chartDemandCaption: "Necessidade de água do perfil da cultura somada ao longo do calendário de plantio.",
  chartCaption: (observed, forecast) => `Observado: ${observed}.${forecast ? ` Previsão: ${forecast}.` : ""}`,
  diagnosisTable: "Diagnóstico: o que os satélites observaram",
  projectionTable: "Projeção: próximos 15 dias",
  languageButton: "EN",
  languageButtonLabel: "Switch to English",
  units: { mm: "mm", mmDay: "mm/dia", days: "dias" },
  crops: { maize: "Milho", beans: "Feijão", cassava: "Mandioca" },
  priorities: { water: "Economizar água", soil: "Proteger o solo", erosion: "Controlar a erosão", income: "Renda" },
  tradeOffLabels: {
    keeps_current_calendar: "Mantém o calendário e a rotina atuais",
    favors_cover_and_soil: "Favorece a cobertura e a saúde do solo",
    favors_forage_or_income: "Favorece forragem e renda",
  },
  strategyTitles: {
    current_practice: "Prática atual",
    soil_water_conservation: "Conservação de solo e água",
    resilient_income_forage: "Renda resiliente e forragem",
  },
  actions: {
    plant_in_window: "Plante durante a janela aberta.",
    wait_for_window: "Espere a janela de plantio.",
    protect_soil: "Mantenha o solo coberto.",
    plant_on_contour: "Plante em curvas de nível.",
    delay_if_dry: "Não plante até o balanço hídrico se recuperar.",
  },
  metrics: {
    rain_total: "Chuva no período",
    forecast_rain_total: "Chuva prevista",
    rain_daily: "Chuva média diária",
    et0_daily: "ET0 média diária",
    water_balance: "Balanço hídrico",
    soil_moisture: "Umidade do solo (superfície)",
    temperature_mean: "Temperatura média",
    temperature_max: "Temperatura máxima",
    ndvi: "Índice de vegetação (NDVI)",
    elevation: "Altitude",
    slope: "Declividade média",
  },
};

export const COPY: Record<Lang, Copy> = { en: EN, "pt-BR": PT };

export const formatDay = (iso: string, lang: Lang): string =>
  new Date(`${iso}T00:00:00Z`).toLocaleDateString(lang === "en" ? "en-GB" : "pt-BR", {
    day: "numeric",
    month: "short",
    year: "numeric",
    timeZone: "UTC",
  });
