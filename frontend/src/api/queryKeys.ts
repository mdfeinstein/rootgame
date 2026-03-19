/**
 * Query Key Factory
 *
 * This file centralizes all TanStack Query keys to ensure consistency,
 * prevent typos, and enable structured cache invalidation.
 */

import { type FactionValue } from "../utils/factionUtils";

export type { FactionValue };

export const gameKeys = {
  all: ["game"] as const,

  // Lists of games
  gameLists: () => [...gameKeys.all, "list"] as const,
  gameList: (type: "active" | "joinable") =>
    [...gameKeys.gameLists(), type] as const,

  // Individual Game Detail
  gameStates: () => [...gameKeys.all, "detail"] as const,
  gameState: (gameId: number) => [...gameKeys.gameStates(), gameId] as const,

  // Sub-resources of a game
  session: (gameId: number) =>
    [...gameKeys.gameState(gameId), "session"] as const,
  clearings: (gameId: number) =>
    [...gameKeys.gameState(gameId), "clearings"] as const,
  players: (gameId: number) =>
    [...gameKeys.gameState(gameId), "players"] as const,
  turnInfo: (gameId: number) =>
    [...gameKeys.gameState(gameId), "turn-info"] as const,
  currentActions: (gameId: number) =>
    [...gameKeys.gameState(gameId), "current-action"] as const,
  currentAction: (gameId: number) => gameKeys.currentActions(gameId),
  currentActionInfos: (gameId: number) =>
    [...gameKeys.gameState(gameId), "current-action-info"] as const,
  currentActionInfo: (gameId: number, route: string | null) =>
    [...gameKeys.currentActionInfos(gameId), route] as const,
  dominanceSupply: (gameId: number) =>
    [...gameKeys.gameState(gameId), "dominance-supply"] as const,
  wsAuth: (gameId: number | string) =>
    [...gameKeys.gameState(Number(gameId)), "ws-auth"] as const,
  revealedCards: (gameId: number) =>
    [...gameKeys.gameState(gameId), "revealed-cards"] as const,

  // Player specific
  playerHand: (gameId: number, username: string) =>
    [...gameKeys.gameState(gameId), "hand", username] as const,

  // Faction specific
  factions: (gameId: number) =>
    [...gameKeys.gameState(gameId), "faction"] as const,
  faction: (gameId: number, faction: FactionValue) =>
    [...gameKeys.factions(gameId), faction?.toUpperCase()] as const,
  factionPrivate: (gameId: number, faction: FactionValue) =>
    [...gameKeys.faction(gameId, faction), "private"] as const,
  craftedCards: (gameId: number, faction: FactionValue) =>
    [...gameKeys.faction(gameId, faction), "crafted-cards"] as const,
};
