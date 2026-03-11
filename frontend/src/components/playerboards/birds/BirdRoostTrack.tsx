import { Box, Paper, SimpleGrid, Stack, Text, Tooltip } from "@mantine/core";
import { IconHome2 } from "@tabler/icons-react";
import ConditionalWrapper from "../../utility/ConditionalWrapper";

const pointPerTurn: number[] = [0, 1, 2, 3, 4, 4, 5];
// Extra draw card icon at these slots
const extraDraws: number[] = [2, 5];

interface BirdRoostTrackProps {
  roostsOnMap: number;
}

export default function BirdRoostTrack({ roostsOnMap }: BirdRoostTrackProps) {
  return (
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
  );
}
