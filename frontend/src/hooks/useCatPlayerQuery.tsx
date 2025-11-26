import { useQuery } from "@tanstack/react-query";

import { useMemo } from "react";
import type { Faction } from "../data/frontend_types";

export type tokensTableType = {
  faction: Faction;
  tokenType: string;
  clearing_number: number;
};

const apiUrl = import.meta.env.VITE_API_URL;
export const useCatPlayerQuery = (gameId: number) => {
  const {
    data: publicInfo,
    isLoading,
    isError,
    isSuccess,
  } = useQuery({
    queryKey: ["catsPublicInfo"],
    queryFn: () =>
      fetch(apiUrl + `/cats/player-info/${gameId}/`).then((r) => r.json()),
  });

  return { publicInfo, isLoading, isError, isSuccess };
};

export default useCatPlayerQuery;
