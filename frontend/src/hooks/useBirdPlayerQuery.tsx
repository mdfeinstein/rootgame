import { useQuery } from "@tanstack/react-query";

const apiUrl = import.meta.env.VITE_API_URL;
export const useBirdPlayerQuery = (gameId: number) => {
  const {
    data: publicInfo,
    isError,
    isLoading,
    isSuccess,
  } = useQuery({
    queryKey: ["birdsPublicInfo"],
    queryFn: () =>
      fetch(apiUrl + `/birds/player-info/${gameId}/`).then((r) => r.json()),
  });

  return { publicInfo, isLoading, isError, isSuccess };
};

export default useBirdPlayerQuery;
