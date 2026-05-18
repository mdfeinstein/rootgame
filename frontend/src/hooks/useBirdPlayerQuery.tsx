import { useQuery } from "@tanstack/react-query";
import { getFactionPlayerInfoQueryOptions } from "./useFactionPlayerInfoQuery";
import type { components } from "../api/types";

export const useBirdPlayerQuery = (
  gameId: number,
  enabled: boolean = true,
): {
  publicInfo: components["schemas"]["Bird"] | undefined;
  isLoading: boolean;
  isError: boolean;
  isSuccess: boolean;
} => {
  const {
    data: publicInfo,
    isError,
    isLoading,
    isSuccess,
  } = useQuery<components["schemas"]["Bird"]>(
    getFactionPlayerInfoQueryOptions<components["schemas"]["Bird"]>(
      gameId,
      "birds",
      enabled,
    ),
  );

  return { publicInfo, isLoading, isError, isSuccess };
};

export default useBirdPlayerQuery;
