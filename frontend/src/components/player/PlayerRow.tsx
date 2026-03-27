import { useContext, useState, useEffect } from "react";
import { GameContext } from "../../contexts/GameProvider";
import useGetPlayersInfoQuery from "../../hooks/useGetPlayersInfoQuery";
import { Group, Button, Text, Stack } from "@mantine/core";
import PlayerIcon from "./PlayerIcon";
import { IconArrowLeft } from "@tabler/icons-react";
import { useNavigate } from "react-router-dom";
import { UserContext } from "../../contexts/UserProvider";
import RevealedCardsHistory from "../board/RevealedCardsHistory";
import DiscardPile from "../board/DiscardPile";
import CraftableItems from "../board/CraftableItems";
import GameLogViewer from "../board/GameLogViewer";

const PlayerRow = () => {
  const { gameId, session } = useContext(GameContext);
  const isGameStarted = session?.status?.label !== "Not Started" && !!session;
  const { players } = useGetPlayersInfoQuery(gameId as number, isGameStarted);
  const sortedPlayers = [...(players || [])].sort(
    (a, b) => a.turn_order - b.turn_order,
  );
  const [openBoardFaction, setOpenBoardFaction] = useState<string | null>(null);
  const { username } = useContext(UserContext);
  const navigate = useNavigate();

  const currentUserPlayer = players?.find(
    (p) => p.username.toLowerCase() === username?.toLowerCase(),
  );

  useEffect(() => {
    const handleContextMenu = (e: MouseEvent) => {
      if (openBoardFaction !== null) {
        e.preventDefault();
        setOpenBoardFaction(null);
      }
    };

    window.addEventListener("contextmenu", handleContextMenu);
    return () => window.removeEventListener("contextmenu", handleContextMenu);
  }, [openBoardFaction]);

  return (
    <Group
      justify="left"
      px="xl"
      wrap="nowrap"
      style={{
        position: "fixed",
        top: 0,
        left: 0,
        width: "100vw",
        zIndex: 1000,
        backgroundColor: "rgba(255, 255, 255, 0.9)",
        paddingTop: "4px",
        paddingBottom: "4px",
        borderBottom: "1px solid #eee",
        boxShadow: "0 4px 12px rgba(0,0,0,0.1)",
        margin: 0,
        overflowX: "auto",
      }}
    >
      <Group wrap="nowrap" style={{ flexShrink: 0 }}>
        <Stack gap={0} align="flex-start">
          <Text size="sm" lh={1}>
            Game #{gameId}
          </Text>
          <Button
            variant="subtle"
            size="compact-sm"
            leftSection={<IconArrowLeft size={14} />}
            onClick={() => navigate("/lobby")}
            px={0}
          >
            Lobby
          </Button>
        </Stack>
        <Stack gap={2} justify="center">
          <Text size="xs" c="dimmed" lh={1}>
            Playing as:
          </Text>
          <Text size="sm" fw={700} lh={1}>
            {currentUserPlayer?.faction.label || "Spectator"}
          </Text>
        </Stack>
      </Group>

      <Group gap="xs" wrap="nowrap" style={{ flexShrink: 0 }}>
        {sortedPlayers.map((player) => (
          <PlayerIcon
            key={player.username}
            player={player}
            isBoardOpen={openBoardFaction === player.faction.value}
            onBoardToggle={() =>
              setOpenBoardFaction((prev) =>
                prev === player.faction.value ? null : player.faction.value,
              )
            }
          />
        ))}
        {gameId && (
          <>
            <RevealedCardsHistory
              gameId={gameId as number}
              isOpen={openBoardFaction === "revealed-cards"}
              onToggle={() =>
                setOpenBoardFaction((prev) =>
                  prev === "revealed-cards" ? null : "revealed-cards",
                )
              }
            />
            <DiscardPile
              gameId={gameId as number}
              isOpen={openBoardFaction === "discard-pile"}
              onToggle={() =>
                setOpenBoardFaction((prev) =>
                  prev === "discard-pile" ? null : "discard-pile",
                )
              }
            />
            <CraftableItems
              gameId={gameId as number}
              isOpen={openBoardFaction === "craftable-items"}
              onToggle={() =>
                setOpenBoardFaction((prev) =>
                  prev === "craftable-items" ? null : "craftable-items",
                )
              }
            />
            <GameLogViewer
              gameId={gameId as number}
              isOpen={openBoardFaction === "game-log"}
              onToggle={() =>
                setOpenBoardFaction((prev) =>
                  prev === "game-log" ? null : "game-log",
                )
              }
            />
          </>
        )}
      </Group>
    </Group>
  );
};

export default PlayerRow;
