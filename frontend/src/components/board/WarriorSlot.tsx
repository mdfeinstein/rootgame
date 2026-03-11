import { useContext } from "react";
import { ClearingContext } from "./Clearing";
import { WarriorTroop } from "./WarriorTroop";
import type { Faction } from "../../data/frontend_types";

export const WarriorSlot = ({
  x,
  y,
  size,
  warriorInfo,
}: {
  x: number;
  y: number;
  size: number;
  warriorInfo: { faction: Faction; count: number } | null;
}) => {
  const ctx = useContext(ClearingContext);
  if (!ctx) throw new Error("Clearing must be nested inside Circle");

  const { cx, cy, r } = ctx;
  const absSize = size * r; // relative to radius
  const absX = cx + x * r - absSize / 2;
  const absY = cy + y * r - absSize / 2;

  return (
    <>
      <rect
        x={absX}
        y={absY}
        width={absSize}
        height={absSize}
        stroke="none"
        fill="none"
      />
      {warriorInfo && warriorInfo.count > 0 && (
        <WarriorTroop
          x={absX}
          y={absY}
          size={absSize}
          count={warriorInfo.count}
          faction={warriorInfo.faction}
        />
      )}
    </>
  );
};
