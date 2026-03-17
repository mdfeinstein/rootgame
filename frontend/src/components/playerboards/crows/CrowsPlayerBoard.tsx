import { Modal, Paper, Stack, Grid, LoadingOverlay } from "@mantine/core";
import { useContext } from "react";
import { GameContext } from "../../../contexts/GameProvider";
import { PlayerContext } from "../../../contexts/PlayerProvider";
import { useCrowPlayerQuery } from "../../../hooks/useCrowPlayerQuery";
import CrowsHeaderSection from "./CrowsHeaderSection";
import CrowsPlotReserve from "./CrowsPlotReserve";
import CrowsTurnFlow from "./CrowsTurnFlow";
import CrowsPlotsSection from "./CrowsPlotsSection";

interface CrowsPlayerBoardProps {
  isOpen: boolean;
  onClose: () => void;
}

export default function CrowsPlayerBoard({
  isOpen,
  onClose,
}: CrowsPlayerBoardProps) {
  const { gameId } = useContext(GameContext);
  const { faction } = useContext(PlayerContext);
  const { publicInfo, privateInfo, isLoading } = useCrowPlayerQuery(
    gameId,
    isOpen,
  );

  if (!publicInfo) return null;

  const isOwner = faction === "Crows";

  const warriorsInSupply = publicInfo.warriors.filter(
    (w) => w.clearing_number === null,
  ).length;

  return (
    <Modal
      opened={isOpen}
      onClose={onClose}
      size="xl"
      centered
      padding={0}
      withCloseButton={false}
      styles={{ content: { background: "transparent", boxShadow: "none" } }}
      overlayProps={{ backgroundOpacity: 0.55, blur: 3 }}
    >
      <Paper
        p="md"
        radius="lg"
        shadow="xl"
        style={{
          backgroundColor: "#fef6e4", // Warm paper background
          border: "4px solid var(--mantine-color-indigo-6)",
          overflow: "hidden",
          position: "relative", // Needed for LoadingOverlay
        }}
      >
        <LoadingOverlay visible={isLoading} overlayProps={{ blur: 2 }} />
        <Stack gap="xs">
          <CrowsHeaderSection warriorsInSupply={warriorsInSupply} />

          <Grid gutter="xs" align="stretch">
            {/* Left Column: Turn Flow */}
            <Grid.Col span={{ base: 12, md: 5 }} style={{ display: "flex" }}>
              <Paper
                withBorder
                p="xs"
                radius="md"
                bg="white"
                shadow="sm"
                style={{ flex: 1 }}
              >
                <CrowsTurnFlow />
              </Paper>
            </Grid.Col>

            {/* Right Column: Plots Reference & Reserve */}
            <Grid.Col span={{ base: 12, md: 7 }} style={{ display: "flex" }}>
              <Stack gap="xs" style={{ flex: 1 }}>
                <CrowsPlotsSection />
                <CrowsPlotReserve
                  reservePlots={privateInfo?.reserve_plots || []}
                  totalCount={publicInfo.reserve_plots_count}
                  isOwner={isOwner}
                />
              </Stack>
            </Grid.Col>
          </Grid>
        </Stack>
      </Paper>
    </Modal>
  );
}
