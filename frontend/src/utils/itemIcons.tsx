import {
  IconShoe,
  IconBriefcase,
  IconCrosshair,
  IconHammer,
  IconSword,
  IconCoffee,
  IconCoin,
  IconTools,
} from "@tabler/icons-react";

export const getItemIcon = (label: string, size: number = 36) => {
  switch (label) {
    case "Boots":
      return <IconShoe size={size} color="#5c5c5c" />;
    case "Bag":
      return <IconBriefcase size={size} color="#5c5c5c" />;
    case "Crossbow":
      return <IconCrosshair size={size} color="#333" />;
    case "Hammer":
      return <IconHammer size={size} color="#4a4a4a" />;
    case "Sword":
      return <IconSword size={size} color="#b0b0b0" />;
    case "Tea":
      return <IconCoffee size={size} color="#7a5c40" />;
    case "Coin":
      return <IconCoin size={size} color="#d4af37" />;
    default:
      return <IconTools size={size} color="black" />;
  }
};
