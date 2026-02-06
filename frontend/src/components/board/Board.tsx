import React, {
  createContext,
  use,
  useContext,
  useEffect,
  useMemo,
  type JSX,
} from "react";

export type Point = { x: number; y: number };

export type Link = { from: string; to: string };
import {
  buildingSlotMap,
  suitMap,
  warriorSlotMap,
  tokenSlotMap,
  defaultPositions,
  defaultLinks,
  waterLinks,
} from "../../data/autumn_map";
import { useQuery } from "@tanstack/react-query";
import { Clearing, type ClearingProps } from "./Clearing";
import { Path } from "./Path";
import { BuildingSlot } from "./BuildingSlot";
import { WarriorSlot } from "./WarriorSlot";
import { TokenSlot, type TokenInfo } from "./TokenSlot";
import useWarriorTable from "../../hooks/useWarriorTable";
import useTokenTable from "../../hooks/useTokenTable";
import useBuildingTable, {
  type BuildingTableType,
} from "../../hooks/useBuildingTable";
import { Roost, Sawmill } from "./Buildings";
import type { Faction } from "../../data/frontend_types";
import { useTurnInfoQuery } from "../../hooks/useTurnInfoQuery";
import { GameContext } from "../../contexts/GameProvider";
import { AspectRatio, Paper } from "@mantine/core";

// Board component: positions, nodes, links, simple viewbox scaling
export default function SvgBoard({
  mapName = "autumn",
  width = 800,
  height = 800,
  onNodeClick,
}: {
  mapName?: "autumn";
  width?: number;
  height?: number;
  onNodeClick?: (id: string) => void;
}) {
  const { gameId, isGameStarted } = useContext(GameContext);
  const turnInfo = useTurnInfoQuery(gameId, isGameStarted);
  useEffect(() => {
    if (!turnInfo.data) return;
    console.log(turnInfo.data);
  }, [turnInfo.data]);

  const factionList: Faction[] = ["Cats", "Birds", "WA"];
  // create list of clearingProps
  const { warriorTable, isSuccess: isSuccessWarrior } = useWarriorTable(
    gameId,
    factionList,
    isGameStarted,
  );

  const { tokenTable, isSuccess: isSuccessToken } = useTokenTable(
    gameId,
    factionList,
    isGameStarted,
  );

  const accumulatedTokens: Record<
    number,
    { faction: Faction; tokenType: string; count: number }[]
  > = useMemo(() => {
    const map: Record<
      number,
      { faction: Faction; tokenType: string; count: number }[]
    > = {};
    for (const token of tokenTable) {
      if (!token.clearing_number) continue;
      if (!map[token.clearing_number]) {
        map[token.clearing_number] = [];
      }
      const sameTokenTypeIdx = map[token.clearing_number].findIndex(
        (t) => t.tokenType === token.tokenType,
      );
      if (sameTokenTypeIdx === -1) {
        map[token.clearing_number].push({
          faction: token.faction,
          tokenType: token.tokenType,
          count: 1,
        });
      } else {
        map[token.clearing_number][sameTokenTypeIdx].count += 1;
      }
    }
    return map;
  }, [tokenTable]);

  const { buildingTable, isSuccess: isSuccessBuilding } = useBuildingTable(
    gameId,
    factionList,
    isGameStarted,
  );

  const buildingInfoByClearingAndSlot = useMemo(() => {
    return (clearingNumber: number, slot: number) => {
      const b = buildingTable.find(
        (b) => b.clearing_number === clearingNumber && b.building_slot === slot,
      );
      if (!b) {
        return null;
      }
      return {
        buildingType: b.buildingType,
        faction: b.faction,
      };
    };
  }, [buildingTable, isSuccessBuilding]);

  const clearingProps: ClearingProps[] = useMemo(() => {
    return defaultPositions.map((pos, i) => {
      const clearingNumber = i + 1;
      const suit = suitMap[clearingNumber];
      return {
        clearingNumber,
        suit,
        circleProps: {
          cx: pos.x * width,
          cy: pos.y * height,
          r: height * 0.08,
        },
      };
    });
  }, [mapName, width, height]);

  // create list of paths
  const pathList = useMemo(() => {
    return defaultLinks.map((link, i) => {
      const a = defaultPositions[link.from - 1];
      const b = defaultPositions[link.to - 1];
      const aScaled = { x: a.x * width, y: a.y * height };
      const bScaled = { x: b.x * width, y: b.y * height };
      return {
        a: aScaled,
        b: bScaled,
        stroke: "brown",
      };
    });
  }, [mapName, width, height]);

  const waterPathList = useMemo(() => {
    return waterLinks.map((link, i) => {
      const a = defaultPositions[link.from - 1];
      const b = defaultPositions[link.to - 1];
      const aScaled = { x: a.x * width, y: a.y * height };
      const bScaled = { x: b.x * width, y: b.y * height };
      return {
        a: aScaled,
        b: bScaled,
        stroke: "blue",
      };
    });
  }, [mapName, width, height]);
  const sq_size = 0.3;

  return (
    <AspectRatio ratio={1 / 1}>
      <Paper shadow="xl" p="md" radius="md" withBorder>
        <svg
          viewBox={`0 0 ${width} ${height}`}
          style={{ width: "100%", height: "100%" }}
        >
          <defs>
            <filter id="shadow" x="-50%" y="-50%" width="200%" height="200%">
              <feDropShadow dx="0" dy="2" stdDeviation="3" floodOpacity="0.2" />
            </filter>
          </defs>
          <g stroke="black" fill="white" filter="url(#shadow)">
            {pathList.map((l, i) => {
              return <Path key={i} a={l.a} b={l.b} stroke={l.stroke} />;
            })}
            {waterPathList.map((l, i) => {
              return (
                <Path
                  key={i}
                  a={l.a}
                  b={l.b}
                  stroke={l.stroke}
                  strokeWidth={10}
                />
              );
            })}
            {clearingProps.map((clearingProp, i) => (
              <Clearing key={i} {...clearingProp}>
                {buildingSlotMap[clearingProp.clearingNumber]?.map((s, i) => (
                  <BuildingSlot
                    key={`b-${i}`}
                    {...s}
                    slot_number={i}
                    buildingInfo={buildingInfoByClearingAndSlot(
                      clearingProp.clearingNumber,
                      i,
                    )}
                  ></BuildingSlot>
                ))}
                {factionList?.map((f, i) => (
                  <WarriorSlot
                    key={`w-${i}`}
                    {...warriorSlotMap[clearingProp.clearingNumber][i]}
                    warriorInfo={{
                      faction: factionList[i],
                      count:
                        warriorTable?.filter(
                          (entry) =>
                            entry.faction === factionList[i] &&
                            entry.clearing_number ===
                              clearingProp.clearingNumber,
                        ).length ?? 0,
                    }}
                  />
                ))}
                {accumulatedTokens[clearingProp.clearingNumber]?.map((t, i) => (
                  <TokenSlot
                    key={`t-${i}`}
                    {...tokenSlotMap[clearingProp.clearingNumber][i]}
                    tokenInfo={{
                      faction: t.faction,
                      tokenType: t.tokenType,
                      count: t.count,
                    }}
                  />
                ))}
              </Clearing>
            ))}
          </g>
        </svg>
      </Paper>
    </AspectRatio>
  );
}
