import { Grid, Modal, Paper, Stack, LoadingOverlay } from "@mantine/core";
import { useContext } from "react";
import { GameContext } from "../../../contexts/GameProvider";
import { PlayerContext } from "../../../contexts/PlayerProvider";
import { type FactionLabel } from "../../../utils/factionUtils";
import useTokenTable from "../../../hooks/useTokenTable";
import useWAPlayerQuery from "../../../hooks/useWAPlayerQuery";
import WaBasesAndOfficers from "./WaBasesAndOfficers";
import WaSupporterSection from "./WaSupporterSection";
import WaSympathyTrack from "./WaSympathyTrack";
import WaHeaderSection from "./WaHeaderSection";
import WaTurnFlow from "./WaTurnFlow";

interface WaPlayerBoardProps {
  isOpen: boolean;
  onClose: () => void;
}

export default function WaPlayerBoard({ isOpen, onClose }: WaPlayerBoardProps) {
  const { gameId } = useContext(GameContext);
  const { faction } = useContext(PlayerContext);
  const { publicInfo, privateInfo, isLoading } = useWAPlayerQuery(
    gameId,
    isOpen,
  );

  if (!publicInfo) return null;

  const { tokenTable } = useTokenTable(
    gameId,
    ["Woodland Alliance" as FactionLabel],
    isOpen,
  );

  const playerIsWA = faction === "Woodland Alliance";
  const tokensOnMap = tokenTable.filter(
    (t) => t.faction === "Woodland Alliance" && t.clearing_number !== null,
  ).length;

  const supporterCount = publicInfo?.supporter_count ?? 0;
  const supporterCards = privateInfo?.supporter_cards;
  const warriors = publicInfo?.warriors ?? [];

  const warriorsInSupply = warriors.filter(
    (w: any) => w.clearing_number === null,
  ).length;

  return (
    <Modal
      opened={isOpen}
      onClose={onClose}
      size="90%"
      centered
      padding={0}
      withCloseButton={false}
      styles={{ content: { background: 'transparent', boxShadow: 'none' } }}
      overlayProps={{ backgroundOpacity: 0.55, blur: 3 }}
    >
      <Paper
        p="md"
        radius="lg"
        shadow="xl"
        style={{
          backgroundColor: "#fef6e4", // Warm paper-like background
          border: "4px solid #28a745",
          overflow: "hidden",
          position: "relative", // Needed for LoadingOverlay
        }}
      >
        <LoadingOverlay visible={isLoading} overlayProps={{ blur: 2 }} />
        <Stack gap="xs">
          <WaHeaderSection warriorsInSupply={warriorsInSupply} />

          <Grid gutter="xs" align="stretch">
            {/* Left Column: Turn Flow */}
            <Grid.Col span={{ base: 12, md: 3 }} style={{ display: 'flex' }}>
              <Paper withBorder p="xs" radius="md" bg="white" shadow="sm" style={{ flex: 1 }}>
                <WaTurnFlow />
              </Paper>
            </Grid.Col>

            {/* Middle Column: Supporters */}
            <Grid.Col span={{ base: 12, md: 3 }} style={{ display: 'flex' }}>
              <WaSupporterSection
                supporterCount={supporterCount}
                playerIsWA={playerIsWA}
                supporterCards={supporterCards}
              />
            </Grid.Col>

            {/* Right Column: Bases/Officers & Sympathy */}
            <Grid.Col span={{ base: 12, md: 6 }} style={{ display: 'flex' }}>
              <Stack gap="xs" style={{ flex: 1 }}>
                <WaBasesAndOfficers
                  bases={publicInfo?.buildings?.base ?? []}
                  officerCount={publicInfo?.officer_count ?? 0}
                />
                <WaSympathyTrack tokensOnMap={tokensOnMap} />
              </Stack>
            </Grid.Col>
          </Grid>
        </Stack>
      </Paper>
    </Modal>
  );
}
