import { useQuery } from "@tanstack/react-query";
import { getFactionPlayerInfoQueryOptions } from "./useFactionPlayerInfoQuery";
import type { components } from "../api/types";

import { type FactionLabel } from "../utils/factionUtils";

export type tokensTableType = {
  faction: FactionLabel;
  tokenType: string;
  clearing_number: number;
};

export const useCatPlayerQuery = (
  gameId: number,
  enabled: boolean = true,
): {
  publicInfo: components["schemas"]["Cat"] | undefined;
  isLoading: boolean;
  isError: boolean;
  isSuccess: boolean;
} => {
  const {
    data: publicInfo,
    isLoading,
    isError,
    isSuccess,
  } = useQuery<components["schemas"]["Cat"]>(
    getFactionPlayerInfoQueryOptions<components["schemas"]["Cat"]>(
      gameId,
      "cats",
      enabled,
    ),
  );

  return { publicInfo, isLoading, isError, isSuccess };
};

export default useCatPlayerQuery;
