export interface MinisterData {
  name: string;
  enum_name: string;
  crown_type: string;
  required_cards: number;
  description: string;
  action_description: string;
}

export interface CrownType {
  display_name: string;
  required_cards: number;
}

const MINISTERS_DATA = {
  marshal: {
    name: "Marshal",
    enum_name: "MARSHAL",
    crown_type: "squire",
    required_cards: 2,
    description: "Take a move.",
    action_description: "Move warriors between clearings.",
  },
  captain: {
    name: "Captain",
    enum_name: "CAPTAIN",
    crown_type: "squire",
    required_cards: 2,
    description: "Initiate a battle.",
    action_description: "Initiate combat.",
  },
  foremole: {
    name: "Foremole",
    enum_name: "FOREMOLE",
    crown_type: "squire",
    required_cards: 2,
    description:
      "Reveal any card to place a citadel or market in any clearing (matching or not) you rule.",
    action_description: "Build without suit restriction.",
  },
  banker: {
    name: "Banker",
    enum_name: "BANKER",
    crown_type: "noble",
    required_cards: 3,
    description:
      "Spend any number of cards (even one) of the same suit to score victory points in equal number.",
    action_description: "Select cards for points.",
  },
  brigadier: {
    name: "Brigadier",
    enum_name: "BRIGADIER",
    crown_type: "noble",
    required_cards: 3,
    description: "Take up to two moves or initiate up to two battles.",
    action_description: "Move or battle (up to twice).",
  },
  mayor: {
    name: "Mayor",
    enum_name: "MAYOR",
    crown_type: "lord",
    required_cards: 4,
    description: "Take the action of any swayed noble or squire.",
    action_description: "Copy any swayed minister's action.",
  },
  duchess: {
    name: "Duchess of Mud",
    enum_name: "DUCHESS_OF_MUD",
    crown_type: "lord",
    required_cards: 4,
    description: "Score two victory points if all three tunnels are on the map.",
    action_description: "Gain points if all tunnels on map.",
  },
  earl: {
    name: "Earl of Stone",
    enum_name: "EARL_OF_STONE",
    crown_type: "lord",
    required_cards: 4,
    description: "Score one victory point per citadel on the map.",
    action_description: "Gain points from citadels.",
  },
  baron: {
    name: "Baron of Dirt",
    enum_name: "BARON_OF_DIRT",
    crown_type: "lord",
    required_cards: 4,
    description: "Score one victory point per market on the map.",
    action_description: "Gain points from markets.",
  },
} as const;

export const CROWN_TYPES: Record<string, CrownType> = {
  squire: {
    display_name: "Squire",
    required_cards: 2,
  },
  noble: {
    display_name: "Noble",
    required_cards: 3,
  },
  lord: {
    display_name: "Lord",
    required_cards: 4,
  },
};

export function getMinisterByName(name: string): MinisterData | undefined {
  return Object.values(MINISTERS_DATA).find((m) => m.name === name);
}

export function getMinisterByEnumName(enumName: string): MinisterData | undefined {
  return Object.values(MINISTERS_DATA).find((m) => m.enum_name === enumName);
}

export function getRequiredCards(crownType: string): number {
  return CROWN_TYPES[crownType]?.required_cards ?? 0;
}

export function getAllMinisters(): MinisterData[] {
  return Object.values(MINISTERS_DATA);
}

export default MINISTERS_DATA;
