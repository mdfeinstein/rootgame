import React, { useContext } from "react";
import { ClearingContext } from "./Clearing";
import { factionToColor } from "./WarriorTroop";
import type { Faction } from "../../data/frontend_types";

export type BuildingType =
  | "roosts"
  | "sawmills"
  | "workshops"
  | "recruiters"
  | "base";

export type BuildingInfo = {
  buildingType: BuildingType;
  faction: Faction;
};

export const BuildingSlot = ({
  x,
  y,
  size,
  slot_number,
  buildingInfo = null,
}: {
  x: number;
  y: number;
  size: number;
  slot_number: number;
  buildingInfo: BuildingInfo | null;
}) => {
  const ctx = useContext(ClearingContext);
  if (!ctx) throw new Error("Square must be nested inside Circle");
  const { cx, cy, r, clearingNumber } = ctx;
  const absSize = size * r; // relative to radius
  const absX = cx + x * r - absSize / 2;
  const absY = cy + y * r - absSize / 2;
  let color = "none";
  let text = "";
  if (buildingInfo) {
    color = factionToColor[buildingInfo.faction];
    text = buildingInfo.buildingType[0];
  }

  return (
    <>
      <rect
        x={absX}
        y={absY}
        width={absSize}
        height={absSize}
        stroke="black"
        fill={color}
      />
      <text
        x={absX + absSize / 2}
        y={absY + (3 * absSize) / 4}
        textAnchor="middle"
        stroke="white"
      >
        {text}
      </text>
    </>
  );
};
