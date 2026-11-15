// AI-assisted: generated with Claude Code, reviewed by <pending Gabriel>
// Text of the immersive map view, in English (default) and Brazilian Portuguese.
import type { Lang } from "../i18n";

export interface ImmersiveCopy {
  product: string;
  tagline: string;
  pilots: string;
  pickHint: string;
  crop: string;
  priority: string;
  recommendation: string;
  waitBecause: (balance: string, threshold: string) => string;
  plantBetween: (crops: string, start: string, end: string) => string;
  onContour: string;
  keepCovered: string;
  confidence: string;
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
  liveAnalysis: string;
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
  crop: "Crop",
  priority: "Priority",
  recommendation: "Recommendation",
  waitBecause: (balance, threshold) => `Wait: the water balance is ${balance} mm, below the severe-deficit limit of ${threshold} mm.`,
  plantBetween: (crops, start, end) => `Plant ${crops} between ${start} and ${end}`,
  onContour: ", on the contour",
  keepCovered: " Keep the soil covered.",
  confidence:
    "How sure is this? The ranking uses fixed agronomic rules. In a 45-season test it barely changed between dry and wet years, so confirm with a local technician.",
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
    `Live analysis of any address needs the analysis service, which is not connected yet. The ranking and the figures below come from the nearest pilot (${name}, ${km} km away); the seasonal rain risk is computed for your point.`,
  liveAnalysis: "Live analysis",
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
  emptyBody: "Type an address, use your location or click the map. You will see when to plant and which of three strategies best withstands a lack of water.",
};

const PT: ImmersiveCopy = {
  product: "Field Shift",
  tagline: "Apoio à decisão de plantio em Sergipe, com dados da NASA",
  pilots: "Talhões piloto",
  pickHint: "Ou clique em qualquer lugar do mapa.",
  crop: "Cultura",
  priority: "Prioridade",
  recommendation: "Recomendação",
  waitBecause: (balance, threshold) =>
    `Espere: o balanço hídrico está em ${balance} mm, abaixo do limite de seca severa de ${threshold} mm.`,
  plantBetween: (crops, start, end) => `Plante ${crops} entre ${start} e ${end}`,
  onContour: ", em curva de nível",
  keepCovered: " Mantenha o solo coberto.",
  confidence:
    "Qual a confiança? O ranking usa regras agronômicas fixas. Num teste com 45 safras ele quase não mudou entre anos secos e chuvosos; confirme com um técnico local.",
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
    `A análise ao vivo de qualquer endereço depende do serviço de análise, que ainda não está ligado. O ranking e os números abaixo vêm do piloto mais próximo (${name}, a ${km} km); o risco de chuva na safra é calculado para o seu ponto.`,
  liveAnalysis: "Análise ao vivo",
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
  emptyBody: "Digite um endereço, use sua localização ou clique no mapa. Você vai ver quando plantar e qual de três estratégias aguenta melhor a falta de água.",
};

export const IMMERSIVE_COPY: Record<Lang, ImmersiveCopy> = { en: EN, "pt-BR": PT };
