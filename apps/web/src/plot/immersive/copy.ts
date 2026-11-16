// AI-assisted: generated with Claude Code, reviewed by <pending Gabriel>
// Text of the immersive map view, in English (default) and Brazilian Portuguese.
import type { Lang } from "../i18n";

export interface ImmersiveCopy {
  product: string;
  tagline: string;
  pilots: string;
  pickHint: string;
  intendedCrop: string;
  lastCrop: string;
  noPreviousCrop: string;
  dateUnavailable: string;
  cropTransition: (lastCrop: string, intendedCrop: string) => string;
  priority: string;
  recommendation: string;
  waitBecause: (balance: string, threshold: string) => string;
  plantBetween: (crops: string, start: string, end: string) => string;
  onContour: string;
  keepCovered: string;
  confidence: string;
  scoreBasis: string;
  backtestLink: string;
  alternatives: string;
  score: string;
  balance: string;
  slope: string;
  forecastRain: string;
  next15: string;
  risk: string;
  riskCaption: (years: string, others: number) => string;
  strongYears: string;
  otherYears: string;
  window: (crop: string) => string;
  riskNote: string;
  months: string[];
  details: string;
  nearestPilot: (name: string, km: number) => string;
  savedRun: (pilot: string, date: string, crop: string, priority: string, savedPrevious: string, selectedPrevious: string, historyMatches: boolean) => string;
  liveAnalysis: string;
  liveNotice: (cell: string) => string;
  close: string;
  openPanel: string;
  addressLabel: string;
  addressPlaceholder: string;
  search: string;
  searching: string;
  useMyLocation: string;
  locating: string;
  myLocation: string;
  searchError: string;
  noResults: string;
  results: string;
  searchCredit: string;
  examples: string;
  outsideSergipe: string;
  riskLoading: string;
  riskUnavailable: string;
  emptyTitle: string;
  emptyBody: string;
}

const EN: ImmersiveCopy = {
  product: "Field Shift",
  tagline: "Planting decision support for Sergipe, built on NASA data",
  pilots: "Pilot plots",
  pickHint: "Or click anywhere on the map.",
  intendedCrop: "Intended crop",
  lastCrop: "Last crop grown",
  noPreviousCrop: "Unknown / none",
  dateUnavailable: "date unavailable",
  cropTransition: (lastCrop, intendedCrop) => `Last grown: ${lastCrop} · Intended: ${intendedCrop}`,
  priority: "Priority",
  recommendation: "Recommendation",
  waitBecause: (balance, threshold) => `Wait: the water balance is ${balance} mm, below the severe-deficit limit of ${threshold} mm.`,
  plantBetween: (crops, start, end) => `Plant ${crops} between ${start} and ${end}`,
  onContour: ", on the contour",
  keepCovered: " Keep the soil covered.",
  confidence:
    "Decision support, not a harvest or yield forecast. The deterministic ranking uses fixed agronomic rules; its top strategy was unchanged in 45 of 45 tested seasons. Confirm choices with a local technician.",
  scoreBasis: "Rule score (0–1), not a yield probability. It combines water, soil, erosion and income fit using the selected priority and available evidence.",
  backtestLink: "See the test",
  alternatives: "Other strategies",
  score: "score",
  balance: "Water balance",
  slope: "Mean slope",
  forecastRain: "Rain forecast",
  next15: "next 15 days",
  risk: "Seasonal rain risk",
  riskCaption: (years, others) =>
    `Median rain per 10-day period at this point, NASA POWER 1981–2025. Strong El Niño seasons (${years}) against the other ${others}.`,
  strongYears: "Strong El Niño years",
  otherYears: "Other years",
  window: (crop) => `Planting window (${crop})`,
  riskNote: "A strong El Niño is under way (NOAA, Nov 2026). Past seasons show risk, not a forecast.",
  months: ["Apr", "May", "Jun", "Jul"],
  details: "All details and sources",
  nearestPilot: (name, km) =>
    `This is a saved example, not a live analysis for your point. The recommendation comes from the nearest pilot (${name}, ${km} km away); seasonal rain risk is computed separately for your point.`,
  savedRun: (pilot, date, crop, priority, savedPrevious, selectedPrevious, historyMatches) =>
    `Saved pilot example: ${pilot}, generated ${date}. Saved inputs: intended crop ${crop}, priority ${priority}, last crop grown ${savedPrevious}. ${historyMatches ? `The saved history matches your selection (${selectedPrevious}).` : `Your selected last crop (${selectedPrevious}) was not applied; this result uses the saved history shown above.`}`,
  liveAnalysis: "Live analysis",
  liveNotice: (cell) =>
    `Live analysis: the engine ran now for your point, on NASA data from the nearest data cell (${cell}).`,
  close: "Close",
  openPanel: "Show the recommendation",
  addressLabel: "Address or place in Sergipe",
  addressPlaceholder: "e.g. Povoado Lagoa Funda, Glória",
  search: "Search",
  searching: "Searching…",
  useMyLocation: "Use my location",
  locating: "Locating…",
  myLocation: "My location",
  searchError: "The search did not work. Check the address or click the map instead.",
  noResults: "No place found in Sergipe with that name. Try the town name or click the map.",
  results: "Places found",
  searchCredit: "Address search © OpenStreetMap contributors (Nominatim).",
  examples: "Examples",
  outsideSergipe: "This point is outside Sergipe. The rules and data are tuned for Sergipe; pick a point inside the state.",
  riskLoading: "Computing the rain risk for this point from NASA POWER…",
  riskUnavailable: "The rain risk for this point could not be loaded from NASA POWER right now.",
  emptyTitle: "Where is the plot?",
  emptyBody: "Type an address, use your location or click the map. Compare three rule-based rotation strategies using the available evidence. This is decision support, not a harvest or yield forecast.",
};

const PT: ImmersiveCopy = {
  product: "Field Shift",
  tagline: "Apoio à decisão de plantio em Sergipe, com dados da NASA",
  pilots: "Talhões piloto",
  pickHint: "Ou clique em qualquer lugar do mapa.",
  intendedCrop: "Cultura pretendida",
  lastCrop: "Última cultura cultivada",
  noPreviousCrop: "Não informado",
  dateUnavailable: "data indisponível",
  cropTransition: (lastCrop, intendedCrop) => `Última cultura: ${lastCrop} · Pretendida: ${intendedCrop}`,
  priority: "Prioridade",
  recommendation: "Recomendação",
  waitBecause: (balance, threshold) =>
    `Espere: o balanço hídrico está em ${balance} mm, abaixo do limite de seca severa de ${threshold} mm.`,
  plantBetween: (crops, start, end) => `Plante ${crops} entre ${start} e ${end}`,
  onContour: ", em curva de nível",
  keepCovered: " Mantenha o solo coberto.",
  confidence:
    "Apoio à decisão, não previsão de colheita ou rendimento. O ranking determinístico usa regras agronômicas fixas; a primeira estratégia ficou igual em 45 de 45 safras testadas. Confirme as escolhas com um técnico local.",
  scoreBasis: "Nota baseada em regras (0–1), não uma probabilidade de rendimento. Combina adequação hídrica, do solo, de erosão e de renda segundo a prioridade e as evidências disponíveis.",
  backtestLink: "Ver o teste",
  alternatives: "Outras estratégias",
  score: "nota",
  balance: "Balanço hídrico",
  slope: "Declividade média",
  forecastRain: "Chuva prevista",
  next15: "próximos 15 dias",
  risk: "Risco de chuva na safra",
  riskCaption: (years, others) =>
    `Chuva mediana por decêndio neste ponto, NASA POWER 1981–2025. Safras de El Niño forte (${years}) contra as outras ${others}.`,
  strongYears: "Anos de El Niño forte",
  otherYears: "Outros anos",
  window: (crop) => `Janela de plantio (${crop})`,
  riskNote: "Há um El Niño forte em curso (NOAA, nov. 2026). As safras passadas mostram risco, não previsão.",
  months: ["abr", "mai", "jun", "jul"],
  details: "Todos os detalhes e fontes",
  nearestPilot: (name, km) =>
    `Este é um exemplo salvo, não uma análise ao vivo do seu ponto. A recomendação vem do piloto mais próximo (${name}, a ${km} km); o risco de chuva na safra é calculado separadamente para o seu ponto.`,
  savedRun: (pilot, date, crop, priority, savedPrevious, selectedPrevious, historyMatches) =>
    `Exemplo salvo do piloto ${pilot}, gerado em ${date}. Entradas salvas: cultura pretendida ${crop}, prioridade ${priority}, última cultura ${savedPrevious}. ${historyMatches ? `O histórico salvo corresponde à sua escolha (${selectedPrevious}).` : `A última cultura escolhida (${selectedPrevious}) não foi aplicada; este resultado usa o histórico salvo acima.`}`,
  liveAnalysis: "Análise ao vivo",
  liveNotice: (cell) =>
    `Análise ao vivo: o motor rodou agora para o seu ponto, com dados da NASA da célula de dados mais próxima (${cell}).`,
  close: "Fechar",
  openPanel: "Ver a recomendação",
  addressLabel: "Endereço ou lugar em Sergipe",
  addressPlaceholder: "ex.: Povoado Lagoa Funda, Glória",
  search: "Buscar",
  searching: "Buscando…",
  useMyLocation: "Usar minha localização",
  locating: "Localizando…",
  myLocation: "Minha localização",
  searchError: "A busca não funcionou. Confira o endereço ou clique no mapa.",
  noResults: "Nenhum lugar com esse nome em Sergipe. Tente o nome da cidade ou clique no mapa.",
  results: "Lugares encontrados",
  searchCredit: "Busca de endereço © colaboradores do OpenStreetMap (Nominatim).",
  examples: "Exemplos",
  outsideSergipe: "Este ponto está fora de Sergipe. As regras e os dados são ajustados para Sergipe; escolha um ponto dentro do estado.",
  riskLoading: "Calculando o risco de chuva deste ponto com a NASA POWER…",
  riskUnavailable: "Não foi possível carregar agora o risco de chuva deste ponto na NASA POWER.",
  emptyTitle: "Onde fica o talhão?",
  emptyBody: "Digite um endereço, use sua localização ou clique no mapa. Compare três estratégias de rotação baseadas em regras e nas evidências disponíveis. Isto apoia decisões, não prevê colheita ou rendimento.",
};

export const IMMERSIVE_COPY: Record<Lang, ImmersiveCopy> = { en: EN, "pt-BR": PT };
