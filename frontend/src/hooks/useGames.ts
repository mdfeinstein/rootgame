import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

const djangoUrl = import.meta.env.VITE_DJANGO_URL;

export interface FactionChoice {
  faction: string;
  faction_label: string;
  chosen: boolean;
}

export interface PlayerInfo {
  username: string;
  faction: string | null;
  faction_label: string;
  score: number;
  turn_order: number | null;
}

export interface GameListItem {
  id: number;
  owner_username: string;
  player_count: number;
  status: string;
  status_label: string;
  user_faction: string | null;
  players?: PlayerInfo[];
  faction_choices?: FactionChoice[];
}

const fetchWithAuth = async (url: string, options: RequestInit = {}) => {
  const token = localStorage.getItem("accessToken");
  const headers = {
    ...options.headers,
    "Content-Type": "application/json",
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  };
  const response = await fetch(url, { ...options, headers });
  if (!response.ok) {
    if (response.status === 401) {
      // Handle unauthorized (optional: refresh token or redirect)
    }
    throw new Error(`HTTP error! status: ${response.status}`);
  }
  return response;
};

export const useActiveGames = () => {
  return useQuery<GameListItem[]>({
    queryKey: ["activeGames"],
    queryFn: async () => {
      const resp = await fetchWithAuth(`${djangoUrl}/api/games/active/`);
      return resp.json();
    },
  });
};

export const useJoinableGames = () => {
  return useQuery<GameListItem[]>({
    queryKey: ["joinableGames"],
    queryFn: async () => {
      const resp = await fetchWithAuth(`${djangoUrl}/api/games/joinable/`);
      return resp.json();
    },
  });
};

export const useCreateGame = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (data: {
      map_label?: string;
      faction_options?: { faction: string }[];
    }) => {
      const resp = await fetchWithAuth(`${djangoUrl}/api/game/create/`, {
        method: "POST",
        body: JSON.stringify(data),
      });
      return resp.json();
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["activeGames"] });
      queryClient.invalidateQueries({ queryKey: ["joinableGames"] });
    },
  });
};

export const useJoinGame = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (gameId: number) => {
      const resp = await fetchWithAuth(
        `${djangoUrl}/api/game/join/${gameId}/`,
        {
          method: "PATCH",
        },
      );
      if (resp.status === 204) return null;
      return resp.json();
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["activeGames"] });
      queryClient.invalidateQueries({ queryKey: ["joinableGames"] });
    },
  });
};

export const useGameSession = (gameId: number | null) => {
  return useQuery<GameListItem>({
    queryKey: ["gameSession", gameId],
    queryFn: async () => {
      const resp = await fetchWithAuth(
        `${djangoUrl}/api/game/${gameId}/session/`,
      );
      return resp.json();
    },
    enabled: !!gameId,
  });
};

export const useStartGame = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (gameId: number) => {
      const resp = await fetchWithAuth(
        `${djangoUrl}/api/game/start/${gameId}/`,
        {
          method: "PATCH",
        },
      );
      if (resp.status === 204) return null;
      return resp.json();
    },
    onSuccess: (_, gameId) => {
      queryClient.invalidateQueries({ queryKey: ["gameSession", gameId] });
    },
  });
};
export const usePickFaction = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (data: { gameId: number; faction: string }) => {
      const resp = await fetchWithAuth(
        `${djangoUrl}/api/game/pick-faction/${data.gameId}/`,
        {
          method: "PATCH",
          body: JSON.stringify({ faction: data.faction }),
        },
      );
      if (resp.status === 204) return null;
      return resp.json();
    },
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({
        queryKey: ["gameSession", variables.gameId],
      });
    },
  });
};
