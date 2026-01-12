import { useQueries } from "@tanstack/react-query";
import type { BuildingType } from "../components/board/BuildingSlot";
import type { Faction } from "../data/frontend_types";
 

export type BuildingTableType = {
  clearing_number: number | null;
  building_slot: number | null;
  faction: Faction;
  buildingType: BuildingType;
};

const tabulateBuildings = (faction: Faction, data: any) => {
  type BuildingItem = {
    player_name: string;
    clearing_number: number;
    building_slot_number: number;
  };
  type BuildingWrapper = {
    building: BuildingItem;
  };
  const buildingTable: BuildingTableType[] = [];
  const buildingData: Record<string, BuildingWrapper[]> = data?.buildings ?? {};
  if (!buildingData) return [];
  for (const buildingType of Object.keys(buildingData)) {
    const buildingsOfType = buildingData[buildingType] ?? [];
    for (const building of buildingsOfType) {
      buildingTable.push({
        faction,
        buildingType: buildingType as BuildingType,
        clearing_number: building.building.clearing_number ?? null,
        building_slot: building.building.building_slot_number ?? null,
      });
    }
  }
  return buildingTable;
};

const apiUrl = import.meta.env.VITE_API_URL;
const useBuildingTable = (gameId: number, factions: string[]) => {
  const results = useQueries({
    queries: factions.map((faction) => ({
      queryKey: [`public-${faction}`],
      queryFn: async () => {
        const response = await fetch(
          apiUrl + `/${faction.toLowerCase()}/player-info/${gameId}/`
        );
        return response.json();
      },
      select: (data) => tabulateBuildings(faction as Faction, data),
    })),
  });

  const isLoading = results.some((r) => r.isLoading);
  const isError = results.some((r) => r.isError);
  const isSuccess = results.every((r) => r.isSuccess);

  const combinedTable = results.flatMap((r) => r.data ?? []);

  return { buildingTable: combinedTable, isLoading, isError, isSuccess };
};

export default useBuildingTable;
