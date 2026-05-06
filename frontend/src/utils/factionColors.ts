import { type FactionLabel } from "./factionUtils";
import { FACTION_CONFIG } from "../data/factionConfig";

const getFactionConfig = (faction: FactionLabel) => {
  return Object.entries(FACTION_CONFIG).find(
    ([, config]) => config.value === faction
  )?.[0];
};

export const factionToColor = (faction: FactionLabel): string => {
  const factionKey = getFactionConfig(faction);
  if (!factionKey) return "#000000";
  return FACTION_CONFIG[factionKey as keyof typeof FACTION_CONFIG].svgColor;
};

export const factionToMantineColor = (faction: FactionLabel): string => {
  const factionKey = getFactionConfig(faction);
  if (!factionKey) return "gray";
  return FACTION_CONFIG[factionKey as keyof typeof FACTION_CONFIG].color;
};
