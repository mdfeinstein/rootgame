import { useQuery } from "@tanstack/react-query";
import { getFactionPlayerInfoQueryOptions } from "./useFactionPlayerInfoQuery";

export const useBirdPlayerQuery = (gameId: number) => {
  const {
    data: publicInfo,
    isError,
    isLoading,
    isSuccess,
  } = useQuery(getFactionPlayerInfoQueryOptions(gameId, "birds"));

  return { publicInfo, isLoading, isError, isSuccess };
};

export default useBirdPlayerQuery;
