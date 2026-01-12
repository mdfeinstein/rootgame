import { useQuery } from "@tanstack/react-query";
import type { CardType } from "./useGetPlayerHandQuery";
import { PlayerContext } from "../contexts/PlayerProvider";
import { useContext } from "react";

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
  const { faction } = useContext(PlayerContext);
  const {
    data: privateInfo,
    isLoading: privateInfoLoading,
    isError: privateInfoError,
    isSuccess: privateInfoSuccess,
  } = useQuery({
    queryKey: ["waPrivateInfo"],
    queryFn: async () => {
      const response = await fetch(
        apiUrl + "/wa/player-private-info/" + gameId + "/",
        {
          headers: {
            Authorization: `Bearer ${localStorage.getItem("accessToken")}`,
            "Content-Type": "application/json",
          },
        }
      );
      return response.json();
    },
    enabled: faction === "WA",
  });
  return {
    publicInfo,
    privateInfo,
    isLoading,
    isError,
    isSuccess,
    privateInfoLoading,
    privateInfoError,
    privateInfoSuccess,
  };
};

export default useWAPlayerQuery;
