import CatPlayerBoard from "../components/playerboards/cats/CatPlayerBoard";
import BirdPlayerBoard from "../components/playerboards/birds/BirdPlayerBoard";
import WaPlayerBoard from "../components/playerboards/wa/WaPlayerBoard";
import CrowsPlayerBoard from "../components/playerboards/crows/CrowsPlayerBoard";

export const FACTION_CONFIG = {
  cats: {
    value: "Cats",
    color: "orange.5",
    abbreviation: "CA",
    boardComponent: CatPlayerBoard,
  },
  birds: {
    value: "Birds",
    color: "blue.5",
    abbreviation: "BI",
    boardComponent: BirdPlayerBoard,
  },
  "woodland-alliance": {
    value: "Woodland Alliance",
    color: "green.3",
    abbreviation: "WA",
    boardComponent: WaPlayerBoard,
  },
  crows: {
    value: "Crows",
    color: "#4B0082",
    abbreviation: "CR",
    boardComponent: CrowsPlayerBoard,
  },
} as const;

export type FactionValue = keyof typeof FACTION_CONFIG;
