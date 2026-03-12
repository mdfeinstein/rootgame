import SvgBoard from "../components/board/Board";
import { GameActionProvider } from "../contexts/GameActionProvider";
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
import PlayerRow from "../components/player/PlayerRow";
import { PlayerProvider } from "../contexts/PlayerProvider";
import UndoButton from "../components/prompts/UndoButton";
import DominanceSupply from "../components/board/DominanceSupply";
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
import useGameWebSocket from "../hooks/useGameWebSocket";

const GamePage = () => {
  const { gameId: urlGameId } = useParams<{ gameId: string }>();
  const { setGameId, session, isGameStarted } = useContext(GameContext);
  const { username } = useContext(UserContext);
  const navigate = useNavigate();
  const startGameMutation = useStartGame();
  const pickFactionMutation = usePickFaction();
  const [selectedFaction, setSelectedFaction] = useState<string | null>(null);

  useGameWebSocket(urlGameId);

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
  const hasCurrentUserPicked = !!currentUserPlayer?.faction?.value;
  const allPlayersPicked = session?.players?.every(
    (p: PlayerInfo) => !!p.faction?.value,
  );
  const isOwner =
    session?.owner_username.toLowerCase() === username?.toLowerCase();

  return (
    <Container size="xl" pt={100} style={{}}>
      <Stack gap="xs">
        {/* Pre-Game Setup Info */}
        {!isGameStarted && session && (
          <Paper
            withBorder
            p="md"
            radius={0}
            shadow="sm"
            style={{ borderTop: "none" }}
          >
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
                <Badge color="orange">
                  {session?.status?.label || "Loading..."}
                </Badge>
                <Text size="sm">
                  Owner: <b>{session?.owner_username}</b>
                </Text>
              </Group>
              <Group>
                {username && isOwner && (
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
                            value: fc.faction.value,
                            label: fc.faction.label,
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
                    You are: {currentUserPlayer?.faction.label}
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
                      {p.faction?.value ? ` (${p.faction.label})` : ""}
                      {idx < arr.length - 1 ? ", " : ""}
                    </Text>
                  ),
                )}
              </Text>
            </Group>
          </Paper>
        )}

        {/* Game Content */}
        {isGameStarted && (
          <PlayerProvider>
            <GameActionProvider>
              <Stack gap="sm" align="center" style={{ paddingBottom: "80px" }}>
                {/* Top Row: Player Row */}
                <PlayerRow />

                {/* Main Content Row */}
                <Group
                  align="flex-start"
                  justify="center"
                  gap="xl"
                  wrap="nowrap"
                  w="100%"
                >
                  {/* Left Column (Board) */}
                  <div
                    style={{
                      width: "800px",
                      height: "670px",
                      position: "relative",
                      zIndex: 1,
                      overflow: "hidden",
                    }}
                  >
                    <SvgBoard width={800} height={800} />
                  </div>

                  {/* Right Column (Sidebar) */}
                  <Stack
                    gap="md"
                    align="stretch"
                    justify="flex-end"
                    w={320}
                    h="100%"
                    style={{ minHeight: "670px" }}
                  >
                    <DominanceSupply />
                    <CraftedCardPrompter />
                    <Prompter />
                    <UndoButton />
                    <DevSignIn />
                  </Stack>
                </Group>

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
