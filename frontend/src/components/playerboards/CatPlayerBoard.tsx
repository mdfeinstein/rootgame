import {
  Box,
  Group,
  Paper,
  Stack,
  Text,
  ThemeIcon,
  Grid,
  Center,
  Modal,
  Tooltip,
} from "@mantine/core";
import {
  IconCampfireFilled,
  IconHammer,
  IconTent,
  IconWood
} from "@tabler/icons-react";

import { useContext } from "react";
import { GameContext } from "../../contexts/GameProvider";
import useBuildingTable from "../../hooks/useBuildingTable";

interface CatPlayerBoardProps {
  isOpen: boolean;
  onClose: () => void;
  // Optional props for backward compatibility or testing if needed, though we'll use the hook primarily
  sawmills?: number;
  workshops?: number;
  recruiters?: number;
}

const WOOD_COSTS = [0, 1, 2, 3, 3, 4];
const SAWMILL_VPS = [0, 1, 2, 3, 4, 5];
const WORKSHOP_VPS = [0, 2, 2, 3, 4, 5];
const RECRUITER_VPS = [0, 1, 2, 3, 3, 4];

const TRACK_CONFIG = [
  {
    label: "Recruiters",
    prop: "recruiters",
    vps: RECRUITER_VPS,
    icon: IconTent, // Fallback or specific
    color: "orange",
  },
  {
    label: "Workshops",
    prop: "workshops",
    vps: WORKSHOP_VPS,
    icon: IconHammer,
    color: "orange",
  },
  {
    label: "Sawmills",
    prop: "sawmills",
    vps: SAWMILL_VPS,
    icon: IconCampfireFilled,
    color: "orange",
  },
];

export default function CatPlayerBoard({
  isOpen,
  onClose,
}: CatPlayerBoardProps) {
  const { gameId } = useContext(GameContext);
  const { buildingTable } = useBuildingTable(gameId, ["Cats"]);
  const catBuildingsOnBoard = buildingTable.filter(
    (b) => b.faction === "Cats" && b.clearing_number === null
  );

  const sawmills = catBuildingsOnBoard.filter(
    (b) => b.buildingType === "sawmills"
  ).length;
  const workshops = catBuildingsOnBoard.filter(
    (b) => b.buildingType === "workshops"
  ).length;
  const recruiters = catBuildingsOnBoard.filter(
    (b) => b.buildingType === "recruiters"
  ).length;

  const counts = { sawmills, workshops, recruiters };

  return (
    <Modal opened={isOpen} onClose={onClose} size="xl" centered>
      <Paper
        p="md"
        radius="lg"
        style={{
          backgroundColor: "var(--mantine-color-orange-1)",
          border: "2px solid var(--mantine-color-orange-6)",
          maxWidth: "800px",
          margin: "0 auto",
        }}
      >
        <Stack gap="lg">
          {/* Title / Header */}
          <Group justify="center">
            <Text
              size="xl"
              fw={900}
              tt="uppercase"
              c="orange.9"
              style={{ letterSpacing: "2px" }}
            >
              Cats
            </Text>
          </Group>

          {/* Tracks */}
          <Box>
            {/* Column Headers (Wood Costs) */}
            <Grid gutter="xs" align="center" mb="xs">
              <Grid.Col span={2}>
                {/* Empty for Row Label */}
              </Grid.Col>
              <Grid.Col span={10}>
                <Grid columns={6} gutter="xs">
                  {WOOD_COSTS.map((cost, i) => (
                    <Grid.Col span={1} key={i}>
                      <Center>
                        <Paper
                          radius="xl"
                          bg="orange.2"
                          w={30}
                          h={30}
                          style={{
                            display: "flex",
                            alignItems: "center",
                            justifyContent: "center",
                          }}
                        >
                          <IconWood />
                          <Text size="sm" fw={700} c="orange.9">
                            {cost}
                          </Text>
                        </Paper>
                      </Center>
                    </Grid.Col>
                  ))}
                </Grid>
              </Grid.Col>
            </Grid>

            {/* Rows */}
            {TRACK_CONFIG.map((track) => {
              const countOnBoard = counts[track.prop as keyof typeof counts];
              const Icon = track.icon;

              return (
                <Grid gutter="xs" align="center" key={track.label} mb="sm">
                  <Grid.Col span={2}>
                    <Text fw={700} size="sm" ta="right" c="dimmed">
                      {track.label}
                    </Text>
                  </Grid.Col>
                  <Grid.Col span={10}>
                    <Grid columns={6} gutter="xs">
                      {track.vps.map((vp, index) => {
                        // Logic: index 0 is valid if countOnBoard > 5?
                        // If countOnBoard is 6, indices 0-5 are filled.
                        // If countOnBoard is 5, indices 1-5 are filled, 0 is empty.
                        // Filled condition: index >= (6 - countOnBoard)
                        const isFilled = index >= 6 - countOnBoard;

                        return (
                          <Grid.Col span={1} key={index}>
                            <Paper
                              radius="md"
                              h={50}
                              withBorder
                              style={{
                                backgroundColor: isFilled
                                  ? "var(--mantine-color-gray-0)"
                                  : "var(--mantine-color-gray-1)",
                                borderColor: isFilled
                                  ? "transparent"
                                  : "var(--mantine-color-gray-3)",
                                display: "flex",
                                alignItems: "center",
                                justifyContent: "center",
                                position: "relative",
                                overflow: "hidden",
                                boxShadow: isFilled
                                  ? "var(--mantine-shadow-sm)"
                                  : "inset 0 2px 4px rgba(0,0,0,0.1)",
                              }}
                            >
                              {/* VP Number (always rendered, covered by building if filled) */}
                              {!isFilled && (
                                <Text fw={800} size="lg" c="gray.5">
                                  +{vp} VP
                                </Text>
                              )}

                              {/* Building Piece */}
                              {isFilled && (
                                <Tooltip label={`+${vp} VP`} withArrow>
                                  <ThemeIcon
                                    size={40}
                                    radius="md"
                                    variant="gradient"
                                    gradient={{
                                      from: `${track.color}.5`,
                                      to: `${track.color}.7`,
                                      deg: 45,
                                    }}
                                  >
                                    <Icon size="60%" color="white" />
                                  </ThemeIcon>
                                </Tooltip>
                              )}
                            </Paper>
                          </Grid.Col>
                        );
                      })}
                    </Grid>
                  </Grid.Col>
                </Grid>
              );
            })}
          </Box>
        </Stack>
      </Paper>
    </Modal>
  );
}
