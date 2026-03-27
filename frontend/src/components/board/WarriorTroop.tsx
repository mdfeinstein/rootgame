import EquilateralTriangle from "../EquilateralTriangle";
import { type FactionLabel } from "../../utils/factionUtils";

export const factionToColor: Record<FactionLabel, string> = {
  Cats: "orange",
  Birds: "blue",
  "Woodland Alliance": "green",
  Crows: "#4B0082",
};

export const WarriorTroop = ({
  x,
  y,
  size,
  count,
  faction,
}: {
  x: number;
  y: number;
  size: number;
  count: number;
  faction: FactionLabel;
}) => {
  const color = factionToColor[faction];
  return (
    <>
      <EquilateralTriangle
        cx={x + size / 2}
        cy={y + size / 2}
        r={size / 2}
        stroke={color}
        fill={color}
      />

      <text
        x={x + size / 2}
        y={y + size * 0.75}
        fontSize={size * 0.75}
        textAnchor="middle"
        stroke="white"
      >
        {count}
      </text>
    </>
  );
};
