import { useQueries } from "@tanstack/react-query";
import type { Faction } from "../data/frontend_types";

export type TokenTableType = {
  faction: Faction;
  tokenType: string;
  clearing_number: number | null;
};

const tabulateTokens = (faction: Faction, data: any) => {
  const tokenTable: TokenTableType[] = [];
  // if (!("tokens" in data)) {
  //   return tokenTable;
  // }
  type TokenItem = {
    player_name: string;
    clearing_number: number;
  };
  type TokenWrapper = {
    token: TokenItem;
  };
  const tokens: Record<string, TokenWrapper[]> = data?.tokens ?? {};
  if (!tokens) return tokenTable;
  for (const tokenType of Object.keys(tokens)) {
    const tokensOfType = tokens[tokenType] ?? [];
    for (const token of tokensOfType) {
      tokenTable.push({
        faction,
        tokenType,
        clearing_number: token.token.clearing_number ?? null,
      });
    }
  }
  return tokenTable;
};

const apiUrl = import.meta.env.VITE_API_URL;
const useTokenTable = (gameId: number, factions: Faction[]) => {
  const results = useQueries({
    queries: factions.map((faction) => ({
      queryKey: [`public-${faction}`],
      queryFn: async () => {
        const response = await fetch(
          apiUrl + `/${faction.toLowerCase()}/player-info/${gameId}/`
        );
        return response.json();
      },
      select: (data) => tabulateTokens(faction, data),
    })),
  });

  const isLoading = results.some((r) => r.isLoading);
  const isError = results.some((r) => r.isError);
  const isSuccess = results.every((r) => r.isSuccess);

  const combinedTable = results.flatMap((r) => r.data ?? []);
  // console.log(combinedTable);

  return { tokenTable: combinedTable, isLoading, isError, isSuccess };
};

export default useTokenTable;
