import { createContext, useContext } from "react";
import { GameActionContext } from "../../contexts/GameActionProvider";
import { Tooltip } from "@mantine/core";

type ClearingContextType = {
  cx: number;
  cy: number;
  r: number;
  clearingNumber: number;
};
export const ClearingContext = createContext<ClearingContextType | null>(null);
export type ClearingProps = {
  clearingNumber: number;
  suit: string;
  circleProps: { cx: number; cy: number; r: number };
  tooltip?: string;
};
// Simple circle node
export function Clearing({
  clearingNumber,
  suit,
  circleProps,
  children,
  onClick,
  tooltip,
}: {
  clearingNumber: number;
  suit: string;
  circleProps: { cx: number; cy: number; r: number };
  children?: React.ReactNode;
  onClick?: (id: number) => void;
  tooltip?: string;
}) {
  const { cx, cy, r } = circleProps;
  const { submitPayloadCallback } = useContext(GameActionContext);
  const submitPayloadOnClick = (clearingNumber: number) => {
    submitPayloadCallback({ clearing_number: clearingNumber });
  };
  return (
    <ClearingContext.Provider value={{ cx, cy, r, clearingNumber }}>
      <Tooltip label={tooltip} disabled={!tooltip} openDelay={500} withArrow>
        <g
          data-id={clearingNumber}
          style={{ cursor: onClick ? "pointer" : "default" }}
          onClick={() => submitPayloadOnClick?.(clearingNumber)}
        >
          <circle cx={cx} cy={cy} r={r} stroke={suit} strokeWidth={6} />
          {children}
        </g>
      </Tooltip>
    </ClearingContext.Provider>
  );
}
