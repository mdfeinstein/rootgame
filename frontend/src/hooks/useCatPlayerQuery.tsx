import { useQuery } from "@tanstack/react-query";
import { getFactionPlayerInfoQueryOptions } from "./useFactionPlayerInfoQuery";

import { type FactionLabel } from "../utils/factionUtils";

export type tokensTableType = {
  faction: FactionLabel;
  tokenType: string;
  clearing_number: number;
};

export const useCatPlayerQuery = (gameId: number) => {
  const {
    data: publicInfo,
    isLoading,
    isError,
    isSuccess,
  } = useQuery(getFactionPlayerInfoQueryOptions(gameId, "cats"));

  return { publicInfo, isLoading, isError, isSuccess };
};

export default useCatPlayerQuery;
