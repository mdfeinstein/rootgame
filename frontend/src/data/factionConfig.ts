import CatPlayerBoard from "../components/playerboards/cats/CatPlayerBoard";
import BirdPlayerBoard from "../components/playerboards/birds/BirdPlayerBoard";
import WaPlayerBoard from "../components/playerboards/wa/WaPlayerBoard";
import CrowsPlayerBoard from "../components/playerboards/crows/CrowsPlayerBoard";
import MolesPlayerBoard from "../components/playerboards/moles/MolesPlayerBoard";

export const FACTION_CONFIG = {
  cats: {
    value: "Cats",
    color: "orange.5",
    svgColor: "orange",
    abbreviation: "CA",
    boardComponent: CatPlayerBoard,
  },
  birds: {
    value: "Birds",
    color: "blue.5",
    svgColor: "blue",
    abbreviation: "BI",
    boardComponent: BirdPlayerBoard,
  },
  "woodland-alliance": {
    value: "Woodland Alliance",
    color: "green.3",
    svgColor: "green",
    abbreviation: "WA",
    boardComponent: WaPlayerBoard,
  },
  crows: {
    value: "Crows",
    color: "#4B0082",
    svgColor: "#4B0082",
    abbreviation: "CR",
    boardComponent: CrowsPlayerBoard,
  },
  moles: {
    value: "Moles",
    color: "#d49d99",
    svgColor: "#d49d99",
    abbreviation: "MO",
    boardComponent: MolesPlayerBoard,
  },
} as const;

export type FactionValue = keyof typeof FACTION_CONFIG;
