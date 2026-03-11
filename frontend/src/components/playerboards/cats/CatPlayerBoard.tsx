import { Group, Modal, Paper, Stack, Text } from "@mantine/core";
import { useContext } from "react";
import { GameContext } from "../../../contexts/GameProvider";
import useBuildingTable from "../../../hooks/useBuildingTable";
import CatBuildingTracks from "./CatBuildingTracks";

interface CatPlayerBoardProps {
  isOpen: boolean;
  onClose: () => void;
}

export default function CatPlayerBoard({
  isOpen,
  onClose,
}: CatPlayerBoardProps) {
  const { gameId } = useContext(GameContext);
  const { buildingTable } = useBuildingTable(gameId, ["Cats"]);
  const catBuildingsOnBoard = buildingTable.filter(
    (b) => b.faction === "Cats" && b.clearing_number === null,
  );

  const sawmills = catBuildingsOnBoard.filter(
    (b) => b.buildingType === "sawmills",
  ).length;
  const workshops = catBuildingsOnBoard.filter(
    (b) => b.buildingType === "workshops",
  ).length;
  const recruiters = catBuildingsOnBoard.filter(
    (b) => b.buildingType === "recruiters",
  ).length;

  const counts = { sawmills, workshops, recruiters };

  return (
    <Modal opened={isOpen} onClose={onClose} size="xl" centered>
      <Paper
        p="md"
        radius="lg"
        style={{
          backgroundColor: "var(--mantine-color-orange-1)",
          border: "2px solid var(--mantine-color-orange-6)",
          maxWidth: "800px",
          margin: "0 auto",
        }}
      >
        <Stack gap="lg">
          {/* Title / Header */}
          <Group justify="center">
            <Text
              size="xl"
              fw={900}
              tt="uppercase"
              c="orange.9"
              style={{ letterSpacing: "2px" }}
            >
              Cats
            </Text>
          </Group>

          {/* Tracks */}
          <CatBuildingTracks counts={counts} />
        </Stack>
      </Paper>
    </Modal>
  );
}
