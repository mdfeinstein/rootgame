import { useQuery } from "@tanstack/react-query";
import { getFactionPlayerInfoQueryOptions } from "./useFactionPlayerInfoQuery";
import { useContext } from "react";
import { PlayerContext } from "../contexts/PlayerProvider";

export type CrowPlayerInfo = {
  player: {
    score: number;
    faction: string;
    username: string;
  };
  warriors: {
    clearing_number: number | null;
  }[];
  reserve_plots_count: number;
  // Add other fields if needed
};

export type CrowPrivateInfo = {
  reserve_plots: {
    id: number;
    plot_type: string;
    clearing_number: number | null;
    is_facedown: boolean;
  }[];
  facedown_plots: {
    id: number;
    plot_type: string;
    clearing_number: number | null;
    is_facedown: boolean;
  }[];
  exposure_revealed_cards: any[];
};

const apiUrl = import.meta.env.VITE_API_URL;

export const useCrowPlayerQuery = (gameId: number, enabled: boolean = true) => {
  const {
    data: publicInfo,
    isLoading: isPublicLoading,
    isError: isPublicError,
    isSuccess: isPublicSuccess,
  } = useQuery<CrowPlayerInfo>({
    ...getFactionPlayerInfoQueryOptions(gameId, "Crows", enabled),
  });

  const { faction } = useContext(PlayerContext);
  const isCrows = faction === "Crows";

  const {
    data: privateInfo,
    isLoading: isPrivateLoading,
    isError: isPrivateError,
    isSuccess: isPrivateSuccess,
  } = useQuery<CrowPrivateInfo>({
    queryKey: ["crowsPrivateInfo", gameId],
    queryFn: async () => {
      const response = await fetch(
        apiUrl + "/crows/player-private-info/" + gameId + "/",
        {
          headers: {
            Authorization: `Bearer ${localStorage.getItem("accessToken")}`,
            "Content-Type": "application/json",
          },
        },
      );
      return response.json();
    },
    enabled: !!gameId && enabled && isCrows,
  });

  return {
    publicInfo,
    privateInfo,
    isLoading: isPublicLoading || (isCrows && isPrivateLoading),
    isError: isPublicError || (isCrows && isPrivateError),
    isSuccess: isPublicSuccess,
    isPrivateSuccess,
  };
};

export default useCrowPlayerQuery;
