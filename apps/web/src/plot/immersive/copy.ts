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
}

const EN: ImmersiveCopy = {
  product: "Field Shift",
  tagline: "Planting decision support for Sergipe, built on NASA data",
  pilots: "Pilot plots",
  pickHint: "Pick a pilot or click the map.",
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
    `Median rain per 10-day period at this pilot, NASA POWER 1981–2025. Strong El Niño seasons (${years}) against the other ${others}.`,
  strongYears: "Strong El Niño years",
  otherYears: "Other years",
  window: (crop) => `Planting window (${crop})`,
  riskNote: "A strong El Niño is under way (NOAA, Nov 2026). Past seasons show risk, not a forecast.",
  months: ["Apr", "May", "Jun", "Jul"],
  details: "All details and sources",
  nearestPilot: (name, km) =>
    `Live analysis for any point is not connected yet. Showing the nearest pilot: ${name}, ${km} km away.`,
  liveAnalysis: "Live analysis",
  close: "Close",
  openPanel: "Show the recommendation",
};

const PT: ImmersiveCopy = {
  product: "Field Shift",
  tagline: "Apoio à decisão de plantio em Sergipe, com dados da NASA",
  pilots: "Talhões piloto",
  pickHint: "Escolha um piloto ou clique no mapa.",
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
    `Chuva mediana por decêndio neste piloto, NASA POWER 1981–2025. Safras de El Niño forte (${years}) contra as outras ${others}.`,
  strongYears: "Anos de El Niño forte",
  otherYears: "Outros anos",
  window: (crop) => `Janela de plantio (${crop})`,
  riskNote: "Há um El Niño forte em curso (NOAA, nov. 2026). As safras passadas mostram risco, não previsão.",
  months: ["abr", "mai", "jun", "jul"],
  details: "Todos os detalhes e fontes",
  nearestPilot: (name, km) =>
    `A análise ao vivo de qualquer ponto ainda não está ligada. Mostrando o piloto mais próximo: ${name}, a ${km} km.`,
  liveAnalysis: "Análise ao vivo",
  close: "Fechar",
  openPanel: "Ver a recomendação",
};

export const IMMERSIVE_COPY: Record<Lang, ImmersiveCopy> = { en: EN, "pt-BR": PT };
