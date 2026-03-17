import { Modal, Paper, Stack, Grid } from "@mantine/core";
import { useContext } from "react";
import { GameContext } from "../../../contexts/GameProvider";
import useBuildingTable from "../../../hooks/useBuildingTable";
import useCatPlayerQuery from "../../../hooks/useCatPlayerQuery";
import CatBuildingTracks from "./CatBuildingTracks";
import CatTurnFlow from "./CatTurnFlow";
import CatHeaderSection from "./CatHeaderSection";

interface CatPlayerBoardProps {
  isOpen: boolean;
  onClose: () => void;
}

export default function CatPlayerBoard({
  isOpen,
  onClose,
}: CatPlayerBoardProps) {
  const { gameId } = useContext(GameContext);
  const { publicInfo } = useCatPlayerQuery(gameId, isOpen);

  if (!publicInfo) return null;

  const warriorsInSupply = publicInfo.warriors.filter(
    (w: any) => w.clearing_number === null,
  ).length;

  const { buildingTable } = useBuildingTable(gameId, ["Cats"], isOpen);
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
    <Modal
      opened={isOpen}
      onClose={onClose}
      size="80%"
      centered
      padding={0}
      withCloseButton={false}
      styles={{ content: { background: 'transparent', boxShadow: 'none' } }}
    >
      <Paper
        p="md"
        radius="lg"
        shadow="xl"
        style={{
          backgroundColor: "#fef6e4", // Warm paper-like background
          border: "4px solid var(--mantine-color-orange-6)",
          overflow: "hidden",
        }}
      >
        <Stack gap="xs">
          <CatHeaderSection warriorsInSupply={warriorsInSupply} />

          <Grid gutter="xs">
            {/* Left Column: Turn Flow */}
            <Grid.Col span={{ base: 12, md: 4 }}>
              <Paper withBorder p="xs" radius="md" bg="white" shadow="sm">
                <CatTurnFlow />
              </Paper>
            </Grid.Col>

            {/* Right Column: Tracks */}
            <Grid.Col span={{ base: 12, md: 8 }}>
              <Stack gap="xs">
                <Paper withBorder p="sm" radius="md" bg="white" shadow="sm">
                  <CatBuildingTracks counts={counts} />
                </Paper>
              </Stack>
            </Grid.Col>
          </Grid>
        </Stack>
      </Paper>
    </Modal>
  );
}
