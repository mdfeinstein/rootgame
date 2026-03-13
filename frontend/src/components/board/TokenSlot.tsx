import { useContext } from "react";
import { ClearingContext } from "./Clearing";
import { Tooltip } from "@mantine/core";

import { factionToColor } from "./WarriorTroop";
import { type FactionLabel } from "../../utils/factionUtils";

export type TokenInfo = {
  faction: FactionLabel;
  tokenType: string;
  count: number;
};
export const TokenSlot = ({
  x,
  y,
  size,
  tokenInfo,
  tooltip,
}: {
  x: number;
  y: number;
  size: number;
  tokenInfo: TokenInfo | null;
  tooltip?: string;
}) => {
  const ctx = useContext(ClearingContext);
  if (!ctx) throw new Error("Square must be nested inside Circle");
  const { cx, cy, r } = ctx;
  const absSize = size * r; // relative to radius
  const absX = cx + x * r - absSize / 2;
  const absY = cy + y * r - absSize / 2;
  let color = "none";
  let text = "";
  let countText = "";
  if (tokenInfo) {
    color = factionToColor[tokenInfo.faction];
    text = tokenInfo.tokenType[0];
    countText = tokenInfo.count > 1 ? tokenInfo.count.toString() : "";
  }
  const token = (
    <>
      <circle
        cx={absX + absSize / 2}
        cy={absY + absSize / 2}
        r={absSize / 2}
        stroke={color}
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
      {countText && (
        <text x={absX} y={absY + absSize} textAnchor="middle" stroke="white">
          {countText}
        </text>
      )}
    </>
  );

  return (
    <Tooltip label={tooltip} disabled={!tooltip} openDelay={0} withArrow>
      <g>
        <rect
          x={absX}
          y={absY}
          width={absSize}
          height={absSize}
          stroke="none"
          fill="none"
        />
        {token}
      </g>
    </Tooltip>
  );
};
