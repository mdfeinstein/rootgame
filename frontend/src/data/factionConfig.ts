import CatPlayerBoard from "../components/playerboards/cats/CatPlayerBoard";
import BirdPlayerBoard from "../components/playerboards/birds/BirdPlayerBoard";
import WaPlayerBoard from "../components/playerboards/wa/WaPlayerBoard";
import CrowsPlayerBoard from "../components/playerboards/crows/CrowsPlayerBoard";

export const FACTION_CONFIG = {
  Cats: {
    value: "Cats",
    color: "orange.5",
    abbreviation: "CA",
    boardComponent: CatPlayerBoard,
  },
  Birds: {
    value: "Birds",
    color: "blue.5",
    abbreviation: "BI",
    boardComponent: BirdPlayerBoard,
  },
  WoodlandAlliance: {
    value: "WoodlandAlliance",
    color: "green.3",
    abbreviation: "WA",
    boardComponent: WaPlayerBoard,
  },
  Crows: {
    value: "Crows",
    color: "indigo.6",
    abbreviation: "CR",
    boardComponent: CrowsPlayerBoard,
  },
  // Backward compatibility keys (if backend still uses abbreviations)
  ca: {
    value: "Cats",
    color: "orange.5",
    abbreviation: "CA",
    boardComponent: CatPlayerBoard,
  },
  bi: {
    value: "Birds",
    color: "blue.5",
    abbreviation: "BI",
    boardComponent: BirdPlayerBoard,
  },
  wa: {
    value: "WoodlandAlliance",
    color: "green.3",
    abbreviation: "WA",
    boardComponent: WaPlayerBoard,
  },
  cr: {
    value: "Crows",
    color: "indigo.6",
    abbreviation: "CR",
    boardComponent: CrowsPlayerBoard,
  },
} as const;

export type FactionValue = keyof typeof FACTION_CONFIG;
