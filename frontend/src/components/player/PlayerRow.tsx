import { useContext, useState, useEffect } from "react";
import { GameContext } from "../../contexts/GameProvider";
import useGetPlayersInfoQuery from "../../hooks/useGetPlayersInfoQuery";
import { Group, Button, Title, Text } from "@mantine/core";
import PlayerIcon from "./PlayerIcon";
import { IconArrowLeft } from "@tabler/icons-react";
import { useNavigate } from "react-router-dom";
import { UserContext } from "../../contexts/UserProvider";

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
      style={{
        position: "fixed",
        top: 0,
        left: 0,
        width: "100vw",
        zIndex: 1000,
        backgroundColor: "rgba(255, 255, 255, 0.9)",
        paddingTop: "10px",
        paddingBottom: "10px",
        borderBottom: "1px solid #eee",
        boxShadow: "0 4px 12px rgba(0,0,0,0.1)",
        margin: 0,
      }}
    >
      <Group>
        <Button
          variant="subtle"
          leftSection={<IconArrowLeft size={16} />}
          onClick={() => navigate("/lobby")}
        >
          Lobby
        </Button>
        <Title order={4}>Game #{gameId}</Title>

        <Text size="sm">
          Playing as: <b>{currentUserPlayer?.faction.label || "Spectator"}</b>
        </Text>
      </Group>

      <Group gap="md">
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
      </Group>
    </Group>
  );
};

export default PlayerRow;
