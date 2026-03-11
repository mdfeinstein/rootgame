import { Modal, Stack } from "@mantine/core";
import { useContext } from "react";
import { GameContext } from "../../../contexts/GameProvider";
import useBirdPlayerQuery from "../../../hooks/useBirdPlayerQuery";
import useBuildingTable from "../../../hooks/useBuildingTable";
import BirdHeaderSection from "./BirdHeaderSection";
import BirdDecreeSection from "./BirdDecreeSection";
import BirdRoostTrack from "./BirdRoostTrack";

interface BirdPlayerBoardProps {
  isOpen: boolean;
  onClose: () => void;
}

export default function BirdPlayerBoard({
  isOpen,
  onClose,
}: BirdPlayerBoardProps) {
  const { gameId } = useContext(GameContext);
  const { publicInfo } = useBirdPlayerQuery(gameId);

  const { buildingTable } = useBuildingTable(gameId, ["Birds"]);
  const roostsOnMap = buildingTable.filter(
    (b) =>
      b.faction === "Birds" &&
      b.buildingType === "roosts" &&
      b.clearing_number !== null,
  ).length;

  const leaders = publicInfo?.leaders ?? [];
  const decree = publicInfo?.decree ?? [];
  const viziers = publicInfo?.viziers ?? [];

  const activeLeader = leaders.find((l: any) => l.active);

  return (
    <Modal
      opened={isOpen}
      onClose={onClose}
      size="xl"
      centered
      overlayProps={{
        backgroundOpacity: 0.55,
        blur: 3,
      }}
    >
      <Stack gap="sm">
        <BirdHeaderSection activeLeader={activeLeader} />
        <BirdDecreeSection decree={decree} viziers={viziers} />
        <BirdRoostTrack roostsOnMap={roostsOnMap} />
      </Stack>
    </Modal>
  );
}
