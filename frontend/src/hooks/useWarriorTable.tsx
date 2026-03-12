import { useQueries } from "@tanstack/react-query";
import type { Faction } from "../data/frontend_types";
import { getFactionPlayerInfoQueryOptions } from "./useFactionPlayerInfoQuery";

export type warriorTableType = {
  clearing_number: number | null;
  faction: Faction;
};

type WarriorType = {
  player_name: string;
  clearing_number: number | null;
};

const tabulateWarriors = (faction: Faction, data: any) => {
  const warriors: WarriorType[] = data.warriors ?? [];
  return warriors.map((warrior: WarriorType): warriorTableType => {
    return { clearing_number: warrior.clearing_number ?? null, faction };
  });
};

const useWarriorTable = (
  gameId: number,
  factions: Faction[],
  enabled: boolean = true,
) => {
  const results = useQueries({
    queries: factions.map((faction) => ({
      ...getFactionPlayerInfoQueryOptions(gameId, faction, enabled),
      select: (data) => tabulateWarriors(faction, data),
    })),
  });

  const isLoading = results.some((r) => r.isLoading);
  const isError = results.some((r) => r.isError);
  const isSuccess = results.every((r) => r.isSuccess);

  const combinedTable = results.flatMap((r) => r.data ?? []);

  return { warriorTable: combinedTable, isLoading, isError, isSuccess };
};

export default useWarriorTable;
