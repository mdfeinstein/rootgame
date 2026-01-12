import {
  Box,
  Group,
  Paper,
  Stack,
  Text,
  Grid,
  Modal,
  Badge,
  ThemeIcon,
  Tooltip,
  SimpleGrid,
  Card,
  Image,
  rem,
} from "@mantine/core";
import {
  IconShoe,
  IconSwords,
  IconHome2, // For Build/Roost
  IconPlus,
  IconCheckbox,
  IconSquare,
} from "@tabler/icons-react";
import { useContext } from "react";
import { GameContext } from "../../contexts/GameProvider";
import useBirdPlayerQuery from "../../hooks/useBirdPlayerQuery";
import useBuildingTable from "../../hooks/useBuildingTable";
import { SUIT_CONFIG } from "../cards/Card";
import ConditionalWrapper from "../utility/ConditionalWrapper";

interface BirdPlayerBoardProps {
  isOpen: boolean;
  onClose: () => void;
}

const pointPerTurn: number[] = [0, 1, 2, 3, 4, 4, 5];
// Extra draw card icon at these slots
const extraDraws: number[] = [2, 5];

const COLUMNS = [
  { label: "Recruit", code: "R", icon: IconPlus, color: "green" },
  { label: "Move", code: "M", icon: IconShoe, color: "blue" },
  { label: "Battle", code: "B", icon: IconSwords, color: "red" },
  { label: "Build", code: "U", icon: IconHome2, color: "yellow" },
];
type Leader = "Builder" | "Charismatic" | "Commander" | "Despot";
const leaderTextMapper: Record<Leader, string> = {
  Builder:
    "Whenever you craft, you ignore your Disdain for Trade special ability",
  Charismatic:
    "Whenever you take a Recruit action, you must place two warriors instead of one.",
  Commander: "In battle as attacker, you deal an extra hit.",
  Despot:
    "Whenever you remove at least one enemy building or token in battle, you score one extra victory point",
};

const columnHelperTextMapper: Record<string, string> = {
  Recruit: "Recruit one warrior at roost in matching clearing.",
  Move: "Move warriors from a matching clearing.",
  Battle: "Battle in a matching clearing",
  Build:
    "Build a roost in a matching clearing that you rule and don't have troops in.",
};

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
      b.clearing_number !== null
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
      <Stack gap="xl">
        {/* Header & Leader Section */}
        <Paper
          p="md"
          radius="md"
          withBorder
          style={{
            borderColor: "var(--mantine-color-blue-6)",
            backgroundColor: "var(--mantine-color-blue-0)",
          }}
        >
          <Group justify="space-between" align="center">
            <Group>
              <ThemeIcon size="xl" radius="md" color="blue" variant="filled">
                <Text fw={900} size="lg">
                  B
                </Text>
              </ThemeIcon>
              <Stack gap={0}>
                <Text size="lg" fw={900} tt="uppercase" c="blue.9">
                  Birds
                </Text>
              </Stack>
            </Group>

            {activeLeader ? (
              <Tooltip
                label={
                  leaderTextMapper[activeLeader.leader_display as Leader] || ""
                }
                multiline
                w={220}
                withArrow
                transitionProps={{ duration: 200, transition: "fade" }}
              >
                <Group>
                  <Stack gap={0} align="flex-end">
                    <Text size="xs" c="dimmed" tt="uppercase" fw={700}>
                      Current Leader
                    </Text>
                    <Text size="lg" fw={800} c="blue.9">
                      {activeLeader.leader_display}
                    </Text>
                  </Stack>
                </Group>
              </Tooltip>
            ) : (
              <Text c="dimmed" fs="italic">
                No Active Leader
              </Text>
            )}
          </Group>
        </Paper>

        {/* Decree Section */}
        <Box>
          <Text size="lg" fw={800} mb="sm" ta="center">
            The Decree
          </Text>
          <SimpleGrid cols={4} spacing="md">
            {COLUMNS.map((col) => {
              const Icon = col.icon;
              const cardsInColumn = decree.filter(
                (d: any) => d.column === col.code
              );
              const viziersInColumn = viziers.filter(
                (v: any) => v.column === col.code
              );
              // Combine viziers (always first?) and cards
              const columnItems = [...viziersInColumn, ...cardsInColumn];

              return (
                <Paper
                  key={col.code}
                  withBorder
                  radius="md"
                  p="sm"
                  style={{
                    backgroundColor: "white",
                    minHeight: "300px",
                    display: "flex",
                    flexDirection: "column",
                  }}
                >
                  {/* Column Header */}
                  <Tooltip
                    label={columnHelperTextMapper[col.label]}
                    multiline
                    w={200}
                    withArrow
                    transitionProps={{ duration: 200, transition: "fade" }}
                  >
                    <Group mb="md" justify="center" gap="xs">
                      <ThemeIcon color={col.color} variant="light">
                        <Icon size={18} />
                      </ThemeIcon>
                      <Text fw={700} tt="uppercase" size="sm">
                        {col.label}
                      </Text>
                    </Group>
                  </Tooltip>

                  {/* Cards Stack */}
                  <Stack gap="xs" style={{ flexGrow: 1 }}>
                    {columnItems.length === 0 && (
                      <Text c="dimmed" size="xs" ta="center" mt="xl">
                        Empty
                      </Text>
                    )}
                    {columnItems.map((item: any, i: number) => {
                      const isVizier = !item.card;
                      const cardData = isVizier
                        ? { title: "Vizier", suit: "b" }
                        : item.card;

                      const suitConfig =
                        SUIT_CONFIG[
                          cardData.suit as keyof typeof SUIT_CONFIG
                        ] || SUIT_CONFIG["b"];
                      const SuitIcon = suitConfig.icon;
                      const StatusIcon = item.fulfilled
                        ? IconCheckbox
                        : IconSquare;

                      return (
                        <Paper
                          key={i}
                          withBorder
                          radius="sm"
                          style={{
                            overflow: "hidden",
                            // Mimic card styling
                            borderColor: "#dee2e6",
                            backgroundColor: "#fff",
                          }}
                        >
                          <Group
                            bg={suitConfig.color}
                            px="xs"
                            py={rem(4)}
                            gap="xs"
                            wrap="nowrap"
                            style={{ color: "white" }}
                          >
                            <SuitIcon size={20} />
                            <Text
                              fw={700}
                              size="xs"
                              style={{
                                letterSpacing: rem(0.5),
                                textTransform: "uppercase",
                              }}
                            >
                              {cardData.title}
                            </Text>
                            <StatusIcon
                              size={18}
                              style={{
                                marginLeft: "auto",
                                opacity: 0.9,
                                minWidth: rem(18), // Ensure it takes up space
                                flexShrink: 0, // Prevent squashing
                              }}
                            />
                          </Group>
                        </Paper>
                      );
                    })}
                  </Stack>
                </Paper>
              );
            })}
          </SimpleGrid>
        </Box>

        {/* Roost Track Section */}
        <Box>
          <Text size="lg" fw={800} mb="sm" ta="center">
            Roosts
          </Text>
          <Paper p="md" radius="md" withBorder bg="gray.1">
            <SimpleGrid cols={7} spacing="xs">
              {pointPerTurn.map((vp, index) => {
                const isFilled = index >= roostsOnMap;
                const isExtraDraw = extraDraws.includes(index);

                return (
                  <Stack key={index} align="center" gap={4}>
                    <ConditionalWrapper
                      condition={isExtraDraw && isFilled}
                      wrapper={(children) => (
                        <Tooltip label="+1 🃏" withArrow>
                          {children}
                        </Tooltip>
                      )}
                    >
                      <Paper
                        w="100%"
                        h={50}
                        withBorder
                        radius="sm"
                        style={{
                          backgroundColor: isFilled
                            ? "var(--mantine-color-blue-2)"
                            : "var(--mantine-color-gray-2)",
                          display: "flex",
                          alignItems: "center",
                          justifyContent: "center",
                          borderColor: isFilled
                            ? "var(--mantine-color-blue-4)"
                            : "var(--mantine-color-gray-4)",
                        }}
                      >
                        {isFilled ? (
                          <IconHome2
                            size={24}
                            color="var(--mantine-color-blue-8)"
                          />
                        ) : (
                          <Stack gap={0} align="center">
                            {isExtraDraw && (
                              <Text size="xs" fw={700}>
                                +1 🃏
                              </Text>
                            )}
                          </Stack>
                        )}
                      </Paper>
                    </ConditionalWrapper>
                    <Text size="sm" fw={700} c="dimmed">
                      +{vp} VP
                    </Text>
                  </Stack>
                );
              })}
            </SimpleGrid>
          </Paper>
        </Box>
      </Stack>
    </Modal>
  );
}
