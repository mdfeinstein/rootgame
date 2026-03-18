import { Modal, Stack, Grid, Paper, LoadingOverlay } from "@mantine/core";
import { useContext } from "react";
import { GameContext } from "../../../contexts/GameProvider";
import useBirdPlayerQuery from "../../../hooks/useBirdPlayerQuery";
import useBuildingTable from "../../../hooks/useBuildingTable";
import BirdHeaderSection from "./BirdHeaderSection";
import BirdDecreeSection from "./BirdDecreeSection";
import BirdRoostTrack from "./BirdRoostTrack";
import BirdTurnFlow from "./BirdTurnFlow";

interface BirdPlayerBoardProps {
  isOpen: boolean;
  onClose: () => void;
}

export default function BirdPlayerBoard({
  isOpen,
  onClose,
}: BirdPlayerBoardProps) {
  const { gameId } = useContext(GameContext);
  const { publicInfo, isLoading } = useBirdPlayerQuery(gameId, isOpen);
  const { buildingTable } = useBuildingTable(gameId, ["Birds"], isOpen);
  const roostsOnMap = buildingTable.filter(
    (b) =>
      b.faction === "Birds" &&
      b.buildingType === "roosts" &&
      b.clearing_number !== null,
  ).length;

  const leaders = publicInfo?.leaders ?? [];
  const decree = publicInfo?.decree ?? [];
  const viziers = publicInfo?.viziers ?? [];
  const warriors = publicInfo?.warriors ?? [];

  const warriorsInSupply = warriors.filter(
    (w: any) => w.clearing_number === null,
  ).length;

  const activeLeader = leaders.find((l: any) => l.active);

  return (
    <Modal
      opened={isOpen}
      onClose={onClose}
      size="80%"
      centered
      padding={0}
      withCloseButton={false}
      styles={{ content: { background: 'transparent', boxShadow: 'none' } }}
      overlayProps={{
        backgroundOpacity: 0.55,
        blur: 3,
      }}
    >
      <Paper
        p="md"
        radius="lg"
        shadow="xl"
        style={{
          backgroundColor: "#fef6e4", // Warm paper-like background
          border: "4px solid var(--mantine-color-blue-6)",
          overflow: "hidden",
          position: "relative",
        }}
      >
        <LoadingOverlay visible={isLoading} overlayProps={{ blur: 2 }} />
        {publicInfo && (
          <Stack gap="xs">
            <BirdHeaderSection
              activeLeader={activeLeader}
              warriorsInSupply={warriorsInSupply}
            />

            <Grid gutter="xs" align="stretch">
              {/* Left Column: Turn Flow */}
              <Grid.Col span={{ base: 12, md: 3 }} style={{ display: "flex" }}>
                <Paper
                  withBorder
                  p="xs"
                  radius="md"
                  bg="white"
                  shadow="sm"
                  style={{ flex: 1 }}
                >
                  <BirdTurnFlow />
                </Paper>
              </Grid.Col>

              {/* Right Column: Tracks and Decree */}
              <Grid.Col span={{ base: 12, md: 9 }} style={{ display: "flex" }}>
                <Stack gap="xs" style={{ flex: 1 }}>
                  <BirdRoostTrack roostsOnMap={roostsOnMap} />
                  <BirdDecreeSection decree={decree} viziers={viziers} />
                </Stack>
              </Grid.Col>
            </Grid>
          </Stack>
        )}
      </Paper>
    </Modal>
  );
}
