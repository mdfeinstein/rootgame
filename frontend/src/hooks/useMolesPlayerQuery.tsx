import { useQuery } from "@tanstack/react-query";
import { getFactionPlayerInfoQueryOptions } from "./useFactionPlayerInfoQuery";
import type { components } from "../api/types";

export const useMolesPlayerQuery = (
  gameId: number,
  enabled: boolean = true,
): {
  publicInfo: components["schemas"]["Moles"] | undefined;
  isLoading: boolean;
  isError: boolean;
  isSuccess: boolean;
} => {
  const {
    data: publicInfo,
    isError,
    isLoading,
    isSuccess,
  } = useQuery<components["schemas"]["Moles"]>(
    getFactionPlayerInfoQueryOptions<components["schemas"]["Moles"]>(
      gameId,
      "moles",
      enabled,
    ),
  );

  return { publicInfo, isLoading, isError, isSuccess };
};

export default useMolesPlayerQuery;
