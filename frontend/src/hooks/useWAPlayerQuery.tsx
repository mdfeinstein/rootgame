import { useQuery } from "@tanstack/react-query";

const apiUrl = import.meta.env.VITE_API_URL;
const useWAPlayerQuery = (gameId: number) => {
  const {
    data: publicInfo,
    isLoading,
    isError,
    isSuccess,
  } = useQuery({
    queryKey: ["waPublicInfo"],
    queryFn: () =>
      fetch(apiUrl + `/wa/player-info/${gameId}/`).then((r) => r.json()),
  });

  return { publicInfo, isLoading, isError, isSuccess };
};

export default useWAPlayerQuery;
