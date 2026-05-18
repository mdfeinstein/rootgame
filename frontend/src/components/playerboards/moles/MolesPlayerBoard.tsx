import { Modal, Stack, Paper, LoadingOverlay, Grid } from "@mantine/core";
import { useContext } from "react";
import { GameContext } from "../../../contexts/GameProvider";
import useMolesPlayerQuery from "../../../hooks/useMolesPlayerQuery";
import useBuildingTable from "../../../hooks/useBuildingTable";
import MolesCitadelTrack from "./MolesCitadelTrack";
import MolesMarketTrack from "./MolesMarketTrack";
import MolesCrownTrack from "./MolesCrownTrack";
import MolesMinisterSection from "./MolesMinisterSection";
import MolesTurnFlow from "./MolesTurnFlow";
import MolesHeaderSection from "./MolesHeaderSection";

interface MolesPlayerBoardProps {
  isOpen: boolean;
  onClose: () => void;
}

export default function MolesPlayerBoard({
  isOpen,
  onClose,
}: MolesPlayerBoardProps) {
  const { gameId } = useContext(GameContext);
  const { publicInfo, isLoading } = useMolesPlayerQuery(gameId, isOpen);
  const { buildingTable } = useBuildingTable(gameId, ["Moles"], isOpen);

  const warriors = publicInfo?.warriors ?? [];
  const warriorsInSupply = warriors.filter(
    (w: any) => w.clearing_number === null,
  ).length;

  const molesBuildingsOnBoard = buildingTable.filter(
    (b) => b.faction === "Moles" && b.clearing_number === null,
  );

  const citadelCount = molesBuildingsOnBoard.filter(
    (b) => b.buildingType === "citadels",
  ).length;
  const marketCount = molesBuildingsOnBoard.filter(
    (b) => b.buildingType === "markets",
  ).length;

  // const tokens = publicInfo?.tokens ?? {};

  const crowns = publicInfo?.crowns ?? [];
  const ministers = publicInfo?.ministers ?? [];

  return (
    <Modal
      opened={isOpen}
      onClose={onClose}
      size="90%"
      centered
      padding={0}
      withCloseButton={false}
      styles={{ content: { background: "transparent", boxShadow: "none" } }}
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
          backgroundColor: "#f5ead6",
          border: "4px solid #d49d99",
          overflow: "hidden",
          position: "relative",
        }}
      >
        <LoadingOverlay visible={isLoading} overlayProps={{ blur: 2 }} />
        {publicInfo && (
          <Stack gap="md">
            {/* Header Section */}
            <MolesHeaderSection
              warriorsInSupply={warriorsInSupply}
              craftedItems={publicInfo?.player?.crafted_items}
            />

            {/* Content Grid */}
            <Grid gutter="md" align="stretch">
              {/* Left Column: Turn Flow */}
              <Grid.Col span={{ base: 12, md: 4 }}>
                <Paper
                  withBorder
                  p="xs"
                  radius="md"
                  bg="white"
                  shadow="sm"
                  style={{ flex: 1 }}
                >
                  <MolesTurnFlow />
                </Paper>
              </Grid.Col>

              {/* Middle Column: Buildings */}
              <Grid.Col span={{ base: 12, md: 4 }}>
                <Stack gap="md">
                  <MolesCitadelTrack citadelCount={citadelCount} />
                  <MolesCrownTrack crowns={crowns} />
                  <MolesMarketTrack marketCount={marketCount} />
                </Stack>
              </Grid.Col>

              {/* Right Column: Ministers */}
              <Grid.Col span={{ base: 12, md: 4 }} style={{ display: "flex" }}>
                <MolesMinisterSection ministers={ministers} />
              </Grid.Col>
            </Grid>
          </Stack>
        )}
      </Paper>
    </Modal>
  );
}
