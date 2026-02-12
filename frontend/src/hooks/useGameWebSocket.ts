import { useEffect, useRef } from "react";
import { useQueryClient } from "@tanstack/react-query";

const useGameWebSocket = (gameId: string | undefined) => {
  const queryClient = useQueryClient();
  const socketRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    if (!gameId) return;

    // Use WS (insecure) or WSS (secure) based on protocol
    // const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    // For now assuming localhost/http for development as per settings
    // const wsUrl = `${protocol}//${window.location.hostname}:8000/ws/game/${gameId}/`;

    let baseUrl = import.meta.env.VITE_DJANGO_URL;

    if (!baseUrl) {
      // If not defined (e.g. production served by same host), use current origin
      baseUrl = window.location.origin;
    }

    // Replace http -> ws, https -> wss
    const wsUrl = baseUrl.replace(/^http/, "ws") + `/ws/game/${gameId}/`;

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
        } else if (data.message === "update") {
          console.log("Game update received, invalidating queries");
          // Invalidate all queries related to the game
          // This might be too broad, can be refined to specific keys
          // For now, let's invalidate everything to be safe and ensure freshness
          queryClient.invalidateQueries();
        }
      };

      socket.onclose = () => {
        console.log("WebSocket disconnected");
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
