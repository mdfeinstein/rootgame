import { useQuery } from "@tanstack/react-query";
import { getFactionPlayerInfoQueryOptions } from "./useFactionPlayerInfoQuery";

import type { Faction } from "../data/frontend_types";

export type tokensTableType = {
  faction: Faction;
  tokenType: string;
  clearing_number: number;
};

export const useCatPlayerQuery = (gameId: number) => {
  const {
    data: publicInfo,
    isLoading,
    isError,
    isSuccess,
  } = useQuery(getFactionPlayerInfoQueryOptions(gameId, "Cats"));

  return { publicInfo, isLoading, isError, isSuccess };
};

export default useCatPlayerQuery;
