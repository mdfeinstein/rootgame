import { Group, Paper, Text, Avatar, rem, Badge } from "@mantine/core";
import { IconTrophy } from "@tabler/icons-react";
import { GameContext } from "../../contexts/GameProvider";
import type { Player } from "../../hooks/useGetPlayersInfoQuery";
import { useContext, useState } from "react";
import CraftedCardBadge from "../cards/CraftedCardBadge";
import CatPlayerBoard from "../playerboards/CatPlayerBoard";
import WaPlayerBoard from "../playerboards/WaPlayerBoard";
import BirdPlayerBoard from "../playerboards/BirdPlayerBoard";

const FACTION_BOARDS: Record<string, React.FC<any>> = {
  ca: CatPlayerBoard,
  Cats: CatPlayerBoard,
  bi: BirdPlayerBoard,
  Birds: BirdPlayerBoard,
  wa: WaPlayerBoard,
  Wolves: WaPlayerBoard,
};

const PlayerIcon = ({ player }: { player: Player }) => {
  // Reuse the suit mapping logic for colors/icons
  const colors = { ca: "orange.5", bi: "blue.5", wa: "green.3" };
  const { faction, username, score } = player;
  const { gameId } = useContext(GameContext);
  const color = colors[faction as keyof typeof colors] || "gray.5";
  const [showBoard, setShowBoard] = useState(false);

  const BoardComponent = FACTION_BOARDS[faction];
  const hasBoard = !!BoardComponent;

  return (
    <>
      <Paper
        withBorder
        p="xs"
        radius="md"
        shadow="sm"
        onClick={() => {
          if (hasBoard) setShowBoard(true);
        }}
        style={{ cursor: hasBoard ? "pointer" : "default" }}
      >
        <Group justify="space-between">
          <Group gap="sm">
            {/* Faction Icon / Avatar */}
            <Avatar color={color} radius="sm" variant="filled">
              {faction.toUpperCase()}
            </Avatar>

            <Text fw={700} size="sm">
              {username}
            </Text>
          </Group>

          {/* Score Badge */}
          <Group gap="xs">
            <CraftedCardBadge
              gameId={gameId}
              faction={faction}
              factionLabel={player.faction_label}
            />
            <Badge
              size="lg"
              variant="light"
              color="gray"
              leftSection={<IconTrophy size={20} />}
            >
              {score}
            </Badge>
          </Group>
        </Group>
      </Paper>
      {BoardComponent && (
        <BoardComponent
          isOpen={showBoard}
          onClose={() => setShowBoard(false)}
        />
      )}
    </>
  );
};

export default PlayerIcon;
