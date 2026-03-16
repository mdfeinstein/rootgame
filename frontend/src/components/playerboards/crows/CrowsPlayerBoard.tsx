import { Modal, Paper, Stack } from "@mantine/core";
import { useContext } from "react";
import { GameContext } from "../../../contexts/GameProvider";
import { useCrowPlayerQuery } from "../../../hooks/useCrowPlayerQuery";
import CrowsAbilities from "./CrowsAbilities";
import CrowsHeaderSection from "./CrowsHeaderSection";
import CrowsPlotReserve from "./CrowsPlotReserve";

interface CrowsPlayerBoardProps {
  isOpen: boolean;
  onClose: () => void;
}

export default function CrowsPlayerBoard({
  isOpen,
  onClose,
}: CrowsPlayerBoardProps) {
  const { gameId } = useContext(GameContext);
  const { publicInfo, privateInfo } = useCrowPlayerQuery(gameId, isOpen);

  if (!publicInfo) return null;

  const warriorsInSupply = publicInfo.warriors.filter(
    (w) => w.clearing_number === null,
  ).length;

  return (
    <Modal
      opened={isOpen}
      onClose={onClose}
      size="lg"
      centered
      title="Corvid Conspiracy Player Board"
    >
      <Paper
        p="md"
        radius="lg"
        style={{
          backgroundColor: "var(--mantine-color-indigo-0)",
          border: "2px solid var(--mantine-color-indigo-6)",
        }}
      >
        <Stack gap="xl">
          <CrowsHeaderSection
            score={publicInfo.player.score}
            warriorsInSupply={warriorsInSupply}
            plotsInSupply={publicInfo.reserve_plots_count}
          />

          {privateInfo && (
            <CrowsPlotReserve reservePlots={privateInfo.reserve_plots} />
          )}

          <CrowsAbilities />
        </Stack>
      </Paper>
    </Modal>
  );
}
