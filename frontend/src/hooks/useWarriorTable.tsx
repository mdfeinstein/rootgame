import { useQueries } from "@tanstack/react-query";
import { type FactionLabel, labelToRoute } from "../utils/factionUtils";
import { getFactionPlayerInfoQueryOptions } from "./useFactionPlayerInfoQuery";
import { type FactionValue } from "../utils/factionUtils";

export type warriorTableType = {
  clearing_number: number | null;
  faction: FactionLabel;
};

type WarriorType = {
  player_name: string;
  clearing_number: number | null;
};

const tabulateWarriors = (faction: FactionLabel, data: any) => {
  const warriors: WarriorType[] = data.warriors ?? [];
  return warriors.map((warrior: WarriorType): warriorTableType => {
    return { clearing_number: warrior.clearing_number ?? null, faction };
  });
};

const useWarriorTable = (
  gameId: number,
  factions: FactionLabel[],
  enabled: boolean = true,
) => {
  const results = useQueries({
    queries: factions.map((faction) => ({
      ...getFactionPlayerInfoQueryOptions(
        gameId,
        labelToRoute(faction) as FactionValue,
        enabled,
      ),
      select: (data: any) => tabulateWarriors(faction, data),
    })),
  });

  const isLoading = results.some((r) => r.isLoading);
  const isError = results.some((r) => r.isError);
  const isSuccess = results.every((r) => r.isSuccess);

  const combinedTable = results.flatMap((r) => r.data ?? []);

  return { warriorTable: combinedTable, isLoading, isError, isSuccess };
};

export default useWarriorTable;
