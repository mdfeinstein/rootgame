import { Box, Grid, Group, Paper, Stack, Text, ThemeIcon, Tooltip } from "@mantine/core";
import { IconPlus } from "@tabler/icons-react";
import { SUIT_CONFIG } from "../../../data/suitConfig";
import type { SuitValue } from "../../../data/suitConfig";

interface WaBasesAndOfficersProps {
  bases: any[];
  officerCount: number;
}

export default function WaBasesAndOfficers({
  bases,
  officerCount,
}: WaBasesAndOfficersProps) {
  return (
    <Paper
      p="xs"
      radius="md"
      shadow="sm"
      withBorder
      style={{
        backgroundColor: "white",
      }}
    >
      <Grid>
        {/* Bases Section */}
        <Grid.Col span={7} style={{ borderRight: "1px dashed #ced4da" }}>
          <Stack align="center" gap={4}>
            <Tooltip
              label="If a base is removed from the map, discard all matching supporters (including birds), and remove half of officers (rounded up). If no bases remain on the map, discard supporters down to 5."
              multiline
              w={250}
              withArrow
              position="bottom"
            >
              <Text
                size="md"
                fw={800}
                tt="uppercase"
                c="dimmed"
                style={{ cursor: "help" }}
              >
                Bases
              </Text>
            </Tooltip>
            <Group justify="center">
              {["r", "y", "o"].map((suit) => {
                const config = SUIT_CONFIG[suit as SuitValue];
                const SuitIcon = config.icon;
                const baseOnMap = bases?.find((b: any) => b.suit.value === suit);
                const isOnPlayerBoard = !baseOnMap;

                return (
                  <Paper
                    key={suit}
                    w={60}
                    h={70}
                    radius="md"
                    style={{
                      backgroundColor: "rgba(255,255,255,0.5)",
                      border: `2px solid ${
                        isOnPlayerBoard ? config.color : "#dee2e6"
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

                    {/* Base Token if on player board (in reserve) */}
                    {isOnPlayerBoard && (
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
                          <IconPlus size={14} color="white" stroke={4} />
                        </div>
                      </ThemeIcon>
                    )}
                  </Paper>
                );
              })}
            </Group>
          </Stack>
        </Grid.Col>

        {/* Officers Section */}
        <Grid.Col span={5}>
          <Stack align="center" gap={4} h="100%">
            <Text size="md" fw={800} tt="uppercase" c="dimmed">
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
                {officerCount}
              </Text>
              <Text size="sm" ta="center" mt="xs" fw={500}>
                1 Military Operation per Officer
              </Text>
            </Box>
          </Stack>
        </Grid.Col>
      </Grid>
    </Paper>
  );
}
