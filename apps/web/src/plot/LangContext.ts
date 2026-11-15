// AI-assisted: generated with Claude Code, reviewed by Periélio (pending human review)
import { createContext, useContext } from "react";
import { COPY, DEFAULT_LANG, type Copy, type Lang } from "./i18n";

export const LangContext = createContext<Lang>(DEFAULT_LANG);

export const useLang = (): Lang => useContext(LangContext);

export const useCopy = (): Copy => COPY[useContext(LangContext)];
