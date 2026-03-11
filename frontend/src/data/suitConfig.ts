import {
  IconBrandFirefox,
  IconCarrot,
  IconFeather,
  IconMickey,
} from "@tabler/icons-react";

export const SUIT_CONFIG = {
  o: { color: "orange.6", icon: IconMickey, label: "Mouse" },
  r: { color: "red.7", icon: IconBrandFirefox, label: "Fox" },
  y: { color: "yellow.5", icon: IconCarrot, label: "Rabbit" },
  b: { color: "blue.6", icon: IconFeather, label: "Bird" },
} as const;

export type SuitValue = keyof typeof SUIT_CONFIG;
