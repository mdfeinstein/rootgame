import { useEffect, useRef } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { gameKeys } from "../api/queryKeys";

const useGameWebSocket = (gameId: string | undefined) => {
  const queryClient = useQueryClient();
  const socketRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    if (!gameId) return;

    // Use WS (insecure) or WSS (secure) based on protocol
    // const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    // For now assuming localhost/http for development as per settings
    // const wsUrl = `${protocol}//${window.location.hostname}:8000/ws/game/${gameId}/`;

    // Use VITE_DJANGO_URL if set (like in local dev), otherwise use the current window host
    const envUrl = import.meta.env.VITE_DJANGO_URL;
    let wsUrl = "";

    if (envUrl) {
      wsUrl = envUrl.replace(/^http/, "ws") + `/ws/game/${gameId}/`;
    } else {
      const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
      wsUrl = `${protocol}//${window.location.host}/ws/game/${gameId}/`;
    }

    const connect = () => {
      const socket = new WebSocket(wsUrl);
      socketRef.current = socket;

      socket.onopen = () => {
        console.log("WebSocket connected");
        const token = localStorage.getItem("accessToken");
        if (token) {
          socket.send(
            JSON.stringify({
              type: "authenticate",
              token: token,
            }),
          );
        } else {
          console.error("No access token found for WebSocket authentication");
          socket.close();
        }
      };

      socket.onmessage = (event) => {
        const data = JSON.parse(event.data);
        if (data.type === "authenticated") {
          console.log("WebSocket authenticated");
          queryClient.setQueryData(gameKeys.wsAuth(gameId), true);
        } else if (data.message === "update") {
          // Invalidate all queries related to the game
          queryClient.invalidateQueries({
            queryKey: gameKeys.gameState(Number(gameId)),
          });
        }
      };

      socket.onclose = () => {
        console.log("WebSocket disconnected");
        queryClient.setQueryData(gameKeys.wsAuth(gameId), false);
        // Reconnect logic could go here
      };

      socket.onerror = (error) => {
        console.error("WebSocket error:", error);
      };
    };

    connect();

    return () => {
      if (socketRef.current) {
        socketRef.current.close();
      }
    };
  }, [gameId, queryClient]);
};

export default useGameWebSocket;
