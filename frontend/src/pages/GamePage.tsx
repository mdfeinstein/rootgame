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
  Container,
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
    <Container size="xl" py="md" style={{ maxWidth: "1200px" }}>
      <Stack gap="xl">
        {/* Top Info Bar */}
        <Paper withBorder p="md" radius="md" shadow="sm">
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
                {session.players?.map(
                  (p: PlayerInfo, idx: number, arr: PlayerInfo[]) => (
                    <Text
                      component="span"
                      key={p.username}
                      fw={p.faction ? 700 : 400}
                    >
                      {p.username}
                      {p.faction ? ` (${p.faction_label})` : ""}
                      {idx < arr.length - 1 ? ", " : ""}
                    </Text>
                  ),
                )}
              </Text>
            </Group>
          )}
        </Paper>

        {/* Game Content */}
        {isGameStarted && (
          <PlayerProvider>
            <GameActionProvider>
              <Stack gap="xl" align="center">
                {/* Sidebar and Board Row */}
                <div
                  style={{
                    display: "flex",
                    justifyContent: "center",
                    width: "100%",
                    minWidth: "1160px",
                    gap: "60px",
                    position: "relative",
                  }}
                >
                  {/* Left Column (Player Info) */}
                  <div
                    style={{
                      width: "300px",
                      position: "relative",
                      zIndex: 10,
                    }}
                  >
                    <Stack gap="md">
                      <PlayerColumn />
                      <UndoButton />
                    </Stack>
                  </div>

                  {/* Right Column (Board) */}
                  <div
                    style={{
                      width: "800px",
                      height: "800px",
                      position: "relative",
                      zIndex: 1,
                      overflow: "hidden",
                    }}
                  >
                    <SvgBoard width={800} height={800} />
                  </div>
                </div>

                {/* Actions Section (Below Row) */}
                <Stack
                  gap="md"
                  align="center"
                  style={{ width: "100%", maxWidth: "800px" }}
                >
                  <CraftedCardPrompter />
                  <Prompter />
                  <DevSignIn />
                </Stack>

                {/* Hand at Bottom */}
                <div style={{ width: "100%" }}>
                  <Hand />
                </div>
              </Stack>
            </GameActionProvider>
          </PlayerProvider>
        )}
      </Stack>
    </Container>
  );
};

export default GamePage;
