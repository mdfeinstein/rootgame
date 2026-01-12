import {
  Modal,
  Grid,
  Paper,
  Stack,
  Text,
  Group,
  ThemeIcon,
  Tooltip,
  Center,
  Box,
  Card,
} from "@mantine/core";
import { IconHandRock, IconCards, IconPlus } from "@tabler/icons-react";
import { useContext } from "react";
import { GameContext } from "../../contexts/GameProvider";
import useWAPlayerQuery from "../../hooks/useWAPlayerQuery";
import useTokenTable from "../../hooks/useTokenTable";
import ConditionalWrapper from "../utility/ConditionalWrapper";
import { SUIT_CONFIG } from "../cards/Card";
import { PlayerContext } from "../../contexts/PlayerProvider";
import type { CardType } from "../../hooks/useGetPlayerHandQuery";

const sympathyPoints = [0, 1, 1, 1, 2, 2, 3, 4, 4, 4];

interface WaPlayerBoardProps {
  isOpen: boolean;
  onClose: () => void;
}

const SupporterStack = () => {
  const { gameId } = useContext(GameContext);
  const { privateInfo, isSuccess } = useWAPlayerQuery(gameId);

  if (!isSuccess || !privateInfo) return null;

  const supporterCards: CardType[] = privateInfo.supporter_cards;
  const counts = {
    fox: supporterCards.filter((c) => c.suit === "r").length,
    rabbit: supporterCards.filter((c) => c.suit === "y").length,
    mouse: supporterCards.filter((c) => c.suit === "o").length,
    bird: supporterCards.filter((c) => c.suit === "b").length,
  };

  return (
    <Card shadow="sm" radius="md" withBorder p="xs" mt="md" w="100%">
      <Text size="sm" fw={700} ta="center" mb="xs">
        Supporter Stack
      </Text>
      <Group justify="space-around">
        <Stack gap={0} align="center">
          <ThemeIcon color="red" variant="light" size="lg">
            <SUIT_CONFIG.r.icon size="1.2rem" />
          </ThemeIcon>
          <Text fw={700}>{counts.fox}</Text>
        </Stack>
        <Stack gap={0} align="center">
          <ThemeIcon color="yellow" variant="light" size="lg">
            <SUIT_CONFIG.y.icon size="1.2rem" />
          </ThemeIcon>
          <Text fw={700}>{counts.rabbit}</Text>
        </Stack>
        <Stack gap={0} align="center">
          <ThemeIcon color="orange" variant="light" size="lg">
            <SUIT_CONFIG.o.icon size="1.2rem" />
          </ThemeIcon>
          <Text fw={700}>{counts.mouse}</Text>
        </Stack>
        <Stack gap={0} align="center">
          <ThemeIcon color="blue" variant="light" size="lg">
            <SUIT_CONFIG.b.icon size="1.2rem" />
          </ThemeIcon>
          <Text fw={700}>{counts.bird}</Text>
        </Stack>
      </Group>
    </Card>
  );
};

export default function WaPlayerBoard({ isOpen, onClose }: WaPlayerBoardProps) {
  const { gameId } = useContext(GameContext);
  const { faction } = useContext(PlayerContext);
  const { publicInfo } = useWAPlayerQuery(gameId);
  const { tokenTable } = useTokenTable(gameId, ["WA"]);
  const playerIsWA = faction === "WA";
  const tokensOnMap = tokenTable.filter(
    (t) => t.faction === "WA" && t.clearing_number !== null
  ).length;
  const tokensOnBoard = 10 - tokensOnMap;

  const supporterCount = publicInfo?.supporter_count ?? 0;

  return (
    <Modal
      opened={isOpen}
      onClose={onClose}
      size="xl"
      centered
      overlayProps={{ backgroundOpacity: 0.55, blur: 3 }}
    >
      <Paper
        p="md"
        radius="lg"
        style={{
          backgroundColor: "#f1f3f5",
          border: "4px solid #40c057",
        }}
      >
        <Grid>
          {/* Left Column: Supporters */}
          <Grid.Col span={3}>
            <Paper
              radius="md"
              h="100%"
              style={{
                backgroundColor: "#2f9e44",
                color: "white",
                display: "flex",
                flexDirection: "column",
                padding: "1rem",
                justifyContent: "space-between",
                border: "2px solid white",
              }}
            >
              <Box>
                <Text
                  fz="h2"
                  fw={900}
                  ta="center"
                  style={{ fontFamily: "serif" }}
                >
                  Supporters
                </Text>
              </Box>

              <Center>
                <Stack align="center" gap={0}>
                  <IconCards size={64} />
                  <Text fz={48} fw={900} lh={1}>
                    {supporterCount}
                  </Text>
                </Stack>
              </Center>

              <Box>
                <Text size="xs" ta="center" c="green.1">
                  If you have no bases on the map, discard any cards that would
                  be added beyond 5.
                </Text>
              </Box>
              {playerIsWA && <SupporterStack />}
            </Paper>
          </Grid.Col>

          {/* Right Column: Bases/Officers & Sympathy */}
          <Grid.Col span={9}>
            <Stack gap="md" h="100%">
              <Paper
                p="sm"
                radius="md"
                style={{
                  backgroundColor: "#fff9db",
                  border: "2px solid #adb5bd", // Changed from dashed to solid to match image style roughly
                }}
              >
                <Grid>
                  {/* Bases Section */}
                  <Grid.Col
                    span={7}
                    style={{ borderRight: "1px dashed #ced4da" }}
                  >
                    <Stack align="center" gap="xs">
                      <Text fz="h3" fw={700} style={{ fontFamily: "serif" }}>
                        Bases
                      </Text>
                      <Group justify="center">
                        {["r", "y", "o"].map((suit) => {
                          const config =
                            SUIT_CONFIG[suit as keyof typeof SUIT_CONFIG];
                          const SuitIcon = config.icon;
                          const base = publicInfo?.buildings?.base?.find(
                            (b: any) => b.suit === suit
                          );
                          const isOnBoard =
                            base?.building?.clearing_number === null;

                          return (
                            <Paper
                              key={suit}
                              w={60}
                              h={70}
                              radius="md"
                              style={{
                                backgroundColor: "rgba(255,255,255,0.5)",
                                border: `2px solid ${
                                  isOnBoard ? config.color : "#dee2e6"
                                }`, // Highlight if present
                                display: "flex",
                                justifyContent: "center",
                                alignItems: "center",
                                position: "relative",
                              }}
                            >
                              {/* Background Icon (always visible as watermark) */}
                              <SuitIcon
                                size={40}
                                color="gray"
                                style={{
                                  opacity: 0.3,
                                  position: "absolute",
                                }}
                              />

                              {/* Base Token if on board */}
                              {isOnBoard && (
                                <ThemeIcon
                                  size={40}
                                  radius="md"
                                  color={config.color}
                                  variant="filled"
                                  style={{ zIndex: 1, position: "relative" }}
                                >
                                  <SuitIcon size={24} color="white" />
                                  <div
                                    style={{
                                      position: "absolute",
                                      top: "50%",
                                      left: "50%",
                                      transform: "translate(-50%, -50%)",
                                    }}
                                  >
                                    <IconPlus
                                      size={14}
                                      color="white"
                                      stroke={4}
                                    />
                                  </div>
                                </ThemeIcon>
                              )}
                            </Paper>
                          );
                        })}
                      </Group>
                      <Text size="xs" lh={1.2}>
                        <Text span fw={700}>
                          Removing Bases.
                        </Text>{" "}
                        If a base is removed from the map, discard all matching
                        supporters (including birds), and remove half of
                        officers (rounded up). If no bases remain on the map,
                        discard supporters down to 5.
                      </Text>
                    </Stack>
                  </Grid.Col>

                  {/* Officers Section (Placeholder for now) */}
                  <Grid.Col span={5}>
                    <Stack align="center" h="100%">
                      <Text fz="h3" fw={700} style={{ fontFamily: "serif" }}>
                        Officers
                      </Text>
                      <Box
                        style={{
                          flexGrow: 1,
                          display: "flex",
                          flexDirection: "column",
                          alignItems: "center",
                          justifyContent: "center",
                        }}
                      >
                        <Text fz={48} fw={900} lh={1}>
                          {publicInfo?.officer_count ?? 0}
                        </Text>
                        <Text size="sm" ta="center" mt="xs" fw={500}>
                          1 Military Operation per Officer
                        </Text>
                      </Box>
                    </Stack>
                  </Grid.Col>
                </Grid>
              </Paper>

              {/* Sympathy Track */}
              <Paper
                p="md"
                radius="md"
                style={{
                  backgroundColor: "#fff9db",
                  border: "1px solid #e9ecef",
                }}
              >
                <Text
                  fz="h3"
                  fw={700}
                  ta="center"
                  mb="md"
                  style={{ fontFamily: "serif" }}
                >
                  Sympathy
                </Text>

                {/* Sympathy Track */}
                <Group justify="center" align="flex-start" gap="md">
                  {[
                    { cost: 1, count: 3, startIndex: 0 },
                    { cost: 2, count: 3, startIndex: 3 },
                    { cost: 3, count: 4, startIndex: 6 },
                  ].map((band) => (
                    <Stack key={band.cost} gap="xs" align="center">
                      {/* Cost Band */}
                      <Paper
                        radius="xs"
                        bg="dark"
                        c="white"
                        fw={900}
                        ta="center"
                        lh={1}
                        py={4}
                        w="100%"
                      >
                        {band.cost}
                      </Paper>

                      {/* Tokens for this band */}
                      <Group gap="sm">
                        {sympathyPoints
                          .slice(band.startIndex, band.startIndex + band.count)
                          .map((vp, i) => {
                            const actualIndex = band.startIndex + i;
                            const isFilled = actualIndex >= tokensOnMap;
                            return (
                              <ConditionalWrapper
                                key={actualIndex}
                                condition={isFilled}
                                wrapper={(children) => (
                                  <Tooltip label={`+${vp} VP`} withArrow>
                                    {children}
                                  </Tooltip>
                                )}
                              >
                                <Box style={{ position: "relative" }}>
                                  <ThemeIcon
                                    size={48}
                                    radius="xl"
                                    color={isFilled ? "green" : "gray.3"}
                                    variant={isFilled ? "filled" : "outline"}
                                    style={{
                                      border: isFilled
                                        ? "none"
                                        : "2px dashed #ced4da",
                                    }}
                                  >
                                    {isFilled ? (
                                      <IconHandRock size={28} />
                                    ) : (
                                      <Text fw={700} c="dimmed">
                                        +{vp}
                                      </Text>
                                    )}
                                  </ThemeIcon>
                                </Box>
                              </ConditionalWrapper>
                            );
                          })}
                      </Group>
                    </Stack>
                  ))}
                </Group>
                <Text size="xs" c="dimmed" mt="sm">
                  Placement Limits: Each clearing may only have one sympathy
                  token.
                </Text>
                <Text size="xs" c="dimmed" mt="sm">
                  Martial Law: Must spend another matching supporter if target
                  clearing has 3+ enemy warriors.
                </Text>
              </Paper>
            </Stack>
          </Grid.Col>
        </Grid>
      </Paper>
    </Modal>
  );
}
