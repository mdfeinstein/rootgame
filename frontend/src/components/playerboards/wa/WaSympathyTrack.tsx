import {
  Box,
  Group,
  Paper,
  Stack,
  Text,
  ThemeIcon,
  Tooltip,
} from "@mantine/core";
import { IconHandRock } from "@tabler/icons-react";
import ConditionalWrapper from "../../utility/ConditionalWrapper";

const SYMPATHY_POINTS = [0, 1, 1, 1, 2, 2, 3, 4, 4, 4];

interface WaSympathyTrackProps {
  tokensOnMap: number;
}

export default function WaSympathyTrack({ tokensOnMap }: WaSympathyTrackProps) {
  return (
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
              {SYMPATHY_POINTS.slice(
                band.startIndex,
                band.startIndex + band.count,
              ).map((vp, i) => {
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
                          border: isFilled ? "none" : "2px dashed #ced4da",
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
        Placement Limits: Each clearing may only have one sympathy token.
      </Text>
      <Text size="xs" c="dimmed" mt="sm">
        Martial Law: Must spend another matching supporter if target clearing
        has 3+ enemy warriors.
      </Text>
    </Paper>
  );
}
