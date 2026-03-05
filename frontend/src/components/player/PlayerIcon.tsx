import { Group, Paper, Text, Avatar, Badge, Tooltip } from "@mantine/core";
import { IconTrophy } from "@tabler/icons-react";
import { GameContext } from "../../contexts/GameProvider";
import type { Player } from "../../hooks/useGetPlayersInfoQuery";
import { useContext } from "react";
import CraftedCardBadge from "../cards/CraftedCardBadge";
import CatPlayerBoard from "../playerboards/CatPlayerBoard";
import WaPlayerBoard from "../playerboards/WaPlayerBoard";
import BirdPlayerBoard from "../playerboards/BirdPlayerBoard";
import CrowsPlayerBoard from "../playerboards/CrowsPlayerBoard";

const FACTION_BOARDS: Record<string, React.FC<any>> = {
  ca: CatPlayerBoard,
  Cats: CatPlayerBoard,
  bi: BirdPlayerBoard,
  Birds: BirdPlayerBoard,
  wa: WaPlayerBoard,
  WoodlandAlliance: WaPlayerBoard,
  cr: CrowsPlayerBoard,
  Crows: CrowsPlayerBoard,
};

const PlayerIcon = ({
  player,
  isBoardOpen,
  onBoardToggle,
}: {
  player: Player;
  isBoardOpen?: boolean;
  onBoardToggle?: () => void;
}) => {
  // Reuse the suit mapping logic for colors/icons
  const colors = {
    ca: "orange.5",
    bi: "blue.5",
    wa: "green.3",
    cr: "indigo.6",
  };
  const suit_colors: Record<string, string> = {
    o: "orange.6",
    r: "red.7",
    y: "yellow.5",
    b: "blue.6",
  };
  const { faction, username, score } = player;
  const { gameId } = useContext(GameContext);
  const color = colors[faction as keyof typeof colors] || "gray.5";

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
          if (hasBoard && onBoardToggle) onBoardToggle();
        }}
        style={{ cursor: hasBoard ? "pointer" : "default" }}
      >
        <Group justify="space-between">
          <Group gap="sm">
            {/* Faction Icon / Avatar */}
            <Tooltip label={username} zIndex={1100}>
              <Avatar color={color} radius="sm" variant="filled">
                {faction.toUpperCase()}
              </Avatar>
            </Tooltip>
          </Group>

          {/* Score Badge */}
          <Group gap="xs">
            <CraftedCardBadge
              gameId={gameId}
              faction={faction}
              factionLabel={player.faction_label}
            />
            {player.active_dominance ? (
              <Badge
                size="lg"
                variant="filled"
                color={
                  suit_colors[player.active_dominance.suit as string] || "gray"
                }
                leftSection={<IconTrophy size={20} />}
              >
                DOM: {player.active_dominance.suit.toUpperCase()}
              </Badge>
            ) : (
              <Badge
                size="lg"
                variant="light"
                color="gray"
                leftSection={<IconTrophy size={20} />}
              >
                {score}
              </Badge>
            )}
          </Group>
        </Group>
      </Paper>
      {BoardComponent && (
        <BoardComponent
          isOpen={isBoardOpen}
          onClose={() => onBoardToggle && onBoardToggle()}
        />
      )}
    </>
  );
};

export default PlayerIcon;
