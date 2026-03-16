import { Grid, Modal, Paper, Stack } from "@mantine/core";
import { useContext } from "react";
import { GameContext } from "../../../contexts/GameProvider";
import { PlayerContext } from "../../../contexts/PlayerProvider";
import { type FactionLabel } from "../../../utils/factionUtils";
import useTokenTable from "../../../hooks/useTokenTable";
import useWAPlayerQuery from "../../../hooks/useWAPlayerQuery";
import WaBasesAndOfficers from "./WaBasesAndOfficers";
import WaSupporterSection from "./WaSupporterSection";
import WaSympathyTrack from "./WaSympathyTrack";

interface WaPlayerBoardProps {
  isOpen: boolean;
  onClose: () => void;
}

export default function WaPlayerBoard({ isOpen, onClose }: WaPlayerBoardProps) {
  const { gameId } = useContext(GameContext);
  const { faction } = useContext(PlayerContext);
  const { publicInfo, privateInfo } = useWAPlayerQuery(gameId, isOpen);
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
  // Fallback to empty array if not WA, since privateInfo might be undefined
  const supporterCards = privateInfo?.supporter_cards;

  return (
    <Modal
      opened={isOpen}
      onClose={onClose}
      size="xl"
      centered
      overlayProps={{ backgroundOpacity: 0.55, blur: 3 }}
    >
      <Paper
        p="md"
        radius="lg"
        style={{
          backgroundColor: "#f1f3f5",
          border: "4px solid #40c057",
        }}
      >
        <Grid>
          {/* Left Column: Supporters */}
          <Grid.Col span={3}>
            <WaSupporterSection
              supporterCount={supporterCount}
              playerIsWA={playerIsWA}
              supporterCards={supporterCards}
            />
          </Grid.Col>

          {/* Right Column: Bases/Officers & Sympathy */}
          <Grid.Col span={9}>
            <Stack gap="md" h="100%">
              {/* Bases and Officers */}
              <WaBasesAndOfficers
                bases={publicInfo?.buildings?.base ?? []}
                officerCount={publicInfo?.officer_count ?? 0}
              />

              {/* Sympathy Track */}
              <WaSympathyTrack tokensOnMap={tokensOnMap} />
            </Stack>
          </Grid.Col>
        </Grid>
      </Paper>
    </Modal>
  );
}
