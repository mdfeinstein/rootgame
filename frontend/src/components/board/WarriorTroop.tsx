import EquilateralTriangle from "../EquilateralTriangle";

export const factionToColor: Record<string, string> = {
  Cats: "orange",
  Birds: "blue",
  WA: "green",
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
  faction: string;
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
