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
      p="xs"
      radius="md"
      shadow="sm"
      withBorder
      style={{
        backgroundColor: "white",
        flex: 1,
      }}
    >
      <Tooltip
        label={
          <Stack gap={4}>
            <Text size="xs">
              Placement Limits: Each clearing may only have one sympathy token.
            </Text>
            <Text size="xs">
              Martial Law: Must spend another matching supporter if target
              clearing has 3+ enemy warriors.
            </Text>
          </Stack>
        }
        multiline
        w={250}
        withArrow
        position="bottom"
      >
        <Text
          size="md"
          fw={800}
          ta="center"
          mb={4}
          tt="uppercase"
          c="dimmed"
          style={{ cursor: "help" }}
        >
          Sympathy
        </Text>
      </Tooltip>

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
    </Paper>
  );
}
