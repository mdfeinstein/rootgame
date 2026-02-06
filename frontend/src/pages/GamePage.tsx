import SvgBoard from "../components/board/Board";
import { GameActionProvider } from "../contexts/GameActionContext";
import Prompter from "../components/board/Prompter";
import CraftedCardPrompter from "../components/board/CraftedCardPrompter";
import DevSignIn from "../components/DevSignIn";
import Hand from "../components/cards/Hand";
import { GameContext } from "../contexts/GameProvider";
import {
  Group,
  Stack,
  Title,
  Button,
  Text,
  Paper,
  Badge,
  Select,
} from "@mantine/core";
import PlayerColumn from "../components/player/PlayerColumn";
import { PlayerProvider } from "../contexts/PlayerProvider";
import UndoButton from "../components/prompts/UndoButton";
import { useParams, useNavigate } from "react-router-dom";
import { useContext, useEffect, useState } from "react";
import {
  useStartGame,
  usePickFaction,
  type PlayerInfo,
  type FactionChoice,
} from "../hooks/useGames";
import {
  IconArrowLeft,
  IconPlayerPlay,
  IconUserCheck,
} from "@tabler/icons-react";
import { UserContext } from "../contexts/UserProvider";

const GamePage = () => {
  const { gameId: urlGameId } = useParams<{ gameId: string }>();
  const { setGameId, session, isGameStarted } = useContext(GameContext);
  const { username } = useContext(UserContext);
  const navigate = useNavigate();
  const startGameMutation = useStartGame();
  const pickFactionMutation = usePickFaction();
  const [selectedFaction, setSelectedFaction] = useState<string | null>(null);

  useEffect(() => {
    if (urlGameId) {
      setGameId(parseInt(urlGameId));
    }
  }, [urlGameId, setGameId]);

  const handleStartGame = () => {
    if (urlGameId) {
      startGameMutation.mutate(parseInt(urlGameId));
    }
  };

  const handlePickFaction = (faction: string) => {
    if (urlGameId) {
      pickFactionMutation.mutate({ gameId: parseInt(urlGameId), faction });
    }
  };

  const currentUserPlayer = session?.players?.find(
    (p: PlayerInfo) => p.username.toLowerCase() === username?.toLowerCase(),
  );
  const hasCurrentUserPicked = !!currentUserPlayer?.faction;
  const allPlayersPicked = session?.players?.every(
    (p: PlayerInfo) => !!p.faction,
  );
  const isOwner =
    session?.owner_username.toLowerCase() === username?.toLowerCase();

  return (
    <Stack gap="md" p="md">
      <Paper withBorder p="xs" radius="md" shadow="sm">
        <Group justify="space-between">
          <Group>
            <Button
              variant="subtle"
              leftSection={<IconArrowLeft size={16} />}
              onClick={() => navigate("/lobby")}
            >
              Lobby
            </Button>
            <Title order={4}>Game #{urlGameId}</Title>
            <Badge color={isGameStarted ? "green" : "orange"}>
              {session?.status_label || "Loading..."}
            </Badge>
            <Text size="sm">
              Owner: <b>{session?.owner_username}</b>
            </Text>
          </Group>
          <Group>
            {!isGameStarted && session && username && isOwner && (
              <Button
                color="green"
                leftSection={<IconPlayerPlay size={16} />}
                loading={startGameMutation.isPending}
                disabled={!allPlayersPicked}
                onClick={handleStartGame}
              >
                Start Game
              </Button>
            )}
          </Group>
        </Group>

        {!isGameStarted && session && (
          <Group mt="md" justify="space-between">
            <Group>
              {!hasCurrentUserPicked && (
                <Group>
                  <Text size="sm" fw={500}>
                    Pick a faction:
                  </Text>
                  <Select
                    placeholder="Choose faction"
                    value={selectedFaction}
                    data={
                      session.faction_choices
                        ?.filter((fc: FactionChoice) => !fc.chosen)
                        .map((fc: FactionChoice) => ({
                          value: fc.faction,
                          label: fc.faction_label,
                        })) || []
                    }
                    onChange={setSelectedFaction}
                  />
                  <Button
                    size="sm"
                    color="blue"
                    leftSection={<IconUserCheck size={16} />}
                    loading={pickFactionMutation.isPending}
                    disabled={!selectedFaction}
                    onClick={() =>
                      selectedFaction && handlePickFaction(selectedFaction)
                    }
                  >
                    Pick Faction
                  </Button>
                </Group>
              )}
              {hasCurrentUserPicked && (
                <Badge
                  variant="filled"
                  color="blue"
                  leftSection={<IconUserCheck size={14} />}
                >
                  You are: {currentUserPlayer?.faction_label}
                </Badge>
              )}
            </Group>
            <Text size="xs" c="dimmed">
              Players:{" "}
              {session.players?.map((p: PlayerInfo) => (
                <Text
                  component="span"
                  key={p.username}
                  fw={p.faction ? 700 : 400}
                >
                  {p.username}
                  {p.faction ? ` (${p.faction_label})` : ""}
                  {p.username !==
                  session.players![session.players!.length - 1].username
                    ? ", "
                    : ""}
                </Text>
              ))}
            </Text>
          </Group>
        )}
      </Paper>

      {isGameStarted && (
        <PlayerProvider>
          <GameActionProvider>
            <Group align="flex-start">
              <Stack>
                <PlayerColumn />
                <UndoButton />
              </Stack>
              <div
                style={{
                  width: "800px",
                  height: "800px",
                }}
              >
                <SvgBoard width={800} height={800} />
              </div>
            </Group>
            <div
              style={{
                display: "flex",
                flexDirection: "column",
              }}
            >
              <div
                style={{
                  display: "flex",
                  flexDirection: "row",
                  alignItems: "center",
                  justifyContent: "center",
                  width: "100%",
                  height: "100%",
                }}
              >
                <Stack>
                  <CraftedCardPrompter />
                  <Prompter />
                </Stack>
              </div>
              <DevSignIn />
            </div>
            <Hand />
          </GameActionProvider>
        </PlayerProvider>
      )}
    </Stack>
  );
};

export default GamePage;
