import { useQuery } from "@tanstack/react-query";
import { getFactionPlayerInfoQueryOptions } from "./useFactionPlayerInfoQuery";

export const useMolesPlayerQuery = (gameId: number, enabled: boolean = true) => {
  const {
    data: publicInfo,
    isError,
    isLoading,
    isSuccess,
  } = useQuery(getFactionPlayerInfoQueryOptions(gameId, "moles", enabled));

  return { publicInfo, isLoading, isError, isSuccess };
};

export default useMolesPlayerQuery;
