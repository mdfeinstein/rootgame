import { Group, Paper, Avatar, Badge, Tooltip } from "@mantine/core";
import { IconTrophy } from "@tabler/icons-react";
import { GameContext } from "../../contexts/GameProvider";
import type { Player } from "../../hooks/useGetPlayersInfoQuery";
import { useContext } from "react";
import CraftedCardBadge from "../cards/CraftedCardBadge";
import { type FactionLabel, labelToRoute } from "../../utils/factionUtils";
import { FACTION_CONFIG } from "../../data/factionConfig";
import type { FactionValue } from "../../data/factionConfig";
import { SUIT_CONFIG } from "../../data/suitConfig";
import type { SuitValue } from "../../data/suitConfig";

const PlayerIcon = ({
  player,
  isBoardOpen,
  onBoardToggle,
}: {
  player: Player;
  isBoardOpen?: boolean;
  onBoardToggle?: () => void;
}) => {
  const { faction, username, score } = player;
  const { gameId } = useContext(GameContext);

  const route = labelToRoute(faction.label as FactionLabel) as FactionValue;
  const factionConfig = FACTION_CONFIG[route];
  const color = factionConfig?.color || "gray.5";
  const BoardComponent = factionConfig?.boardComponent;
  const hasBoard = !!BoardComponent;

  return (
    <>
      <Paper
        withBorder
        p="0.2rem"
        radius="md"
        shadow="sm"
        onClick={() => {
          if (hasBoard && onBoardToggle) onBoardToggle();
        }}
        style={{ cursor: hasBoard ? "pointer" : "default" }}
      >
        <Group justify="space-between" gap="0.1rem">
          <Group gap="0.1rem">
            {/* Faction Icon / Avatar */}
            <Tooltip label={username} zIndex={1100}>
              <Avatar color={color} radius="sm" variant="filled">
                {factionConfig?.abbreviation ||
                  faction.value.substring(0, 2).toUpperCase()}
              </Avatar>
            </Tooltip>
          </Group>

          {/* Score Badge */}
          <Group gap="0.1rem">
            <CraftedCardBadge
              gameId={gameId as number}
              faction={labelToRoute(faction.label as FactionLabel) as any}
              factionLabel={faction.label}
            />
            {player.active_dominance ? (
              <Badge
                size="lg"
                variant="filled"
                color={
                  SUIT_CONFIG[player.active_dominance as SuitValue]?.color ||
                  "gray"
                }
                leftSection={<IconTrophy size={20} />}
              >
                DOM: {player.active_dominance.toUpperCase()}
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
          isOpen={isBoardOpen || false}
          onClose={() => onBoardToggle && onBoardToggle()}
        />
      )}
    </>
  );
};

export default PlayerIcon;
