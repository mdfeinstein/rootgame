import { QueryClient } from "@tanstack/react-query";
import { gameKeys } from "../api/queryKeys";

// Expose to window for console access
declare global {
  interface Window {
    mockCraftedItems: {
      inject: (faction: string, items: any[]) => void;
      catsWithBootsAndCoin: () => void;
      birdsWithMultiple: () => void;
      clear: (faction: string) => void;
    };
  }
}

let queryClientInstance: QueryClient | null = null;
let gameIdInstance: number | null = null;

export function initDevConsole(queryClient: QueryClient, gameId: number) {
  queryClientInstance = queryClient;
  gameIdInstance = gameId;

  window.mockCraftedItems = {
    inject: (faction: string, items: any[]) => {
      if (!queryClientInstance || !gameIdInstance) {
        console.error("Dev console not initialized. Open a player board first.");
        return;
      }

      const factionMap: Record<string, "cats" | "birds" | "crows" | "woodland-alliance"> = {
        cats: "cats",
        ca: "cats",
        birds: "birds",
        bi: "birds",
        crows: "crows",
        cr: "crows",
        wa: "woodland-alliance",
        "woodland-alliance": "woodland-alliance",
      };

      const mappedFaction = factionMap[faction.toLowerCase()];
      if (!mappedFaction) {
        console.error(
          `Unknown faction: ${faction}. Use: cats, birds, crows, or wa`
        );
        return;
      }

      const currentData = queryClientInstance!.getQueryData(
        gameKeys.faction(gameIdInstance!, mappedFaction)
      );

      if (currentData) {
        queryClientInstance!.setQueryData(
          gameKeys.faction(gameIdInstance!, mappedFaction),
          {
            ...currentData,
            crafted_items: items,
          }
        );
        console.log(
          `✓ Injected ${items.length} crafted items for ${mappedFaction}`
        );
      } else {
        console.error(
          `No query data found for ${mappedFaction}. Make sure the player board is open.`
        );
      }
    },

    catsWithBootsAndCoin: () => {
      window.mockCraftedItems.inject("cats", [
        {
          id: 1,
          item: { value: "1", label: "Boots" },
          exhausted: true,
        },
        {
          id: 2,
          item: { value: "3", label: "Coin" },
          exhausted: false,
        },
      ]);
    },

    birdsWithMultiple: () => {
      window.mockCraftedItems.inject("birds", [
        {
          id: 1,
          item: { value: "4", label: "Crossbow" },
          exhausted: false,
        },
        {
          id: 2,
          item: { value: "6", label: "Sword" },
          exhausted: false,
        },
        {
          id: 3,
          item: { value: "0", label: "Bag" },
          exhausted: true,
        },
        {
          id: 4,
          item: { value: "2", label: "Coin" },
          exhausted: false,
        },
        {
          id: 5,
          item: { value: "5", label: "Hammer" },
          exhausted: true,
        },
        {
          id: 6,
          item: { value: "1", label: "Boots" },
          exhausted: false,
        },
        {
          id: 7,
          item: { value: "3", label: "Tea" },
          exhausted: true,
        },
      ]);
    },

    clear: (faction: string) => {
      window.mockCraftedItems.inject(faction, []);
    },
  };

  console.log(
    "✓ Dev console ready! Use window.mockCraftedItems in the console.\n" +
      "Available commands:\n" +
      "  mockCraftedItems.catsWithBootsAndCoin()\n" +
      "  mockCraftedItems.birdsWithMultiple()\n" +
      "  mockCraftedItems.inject('faction', items)\n" +
      "  mockCraftedItems.clear('faction')"
  );
}
