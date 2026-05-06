import { Paper, SimpleGrid, Stack, Text, Tooltip } from "@mantine/core";
import { IconSwords } from "@tabler/icons-react";

const CITADEL_BONUSES = ["+1 Warrior", "+2 Warrior", "+2 Warrior"];

interface MolesCitadelTrackProps {
  citadelCount: number;
}

export default function MolesCitadelTrack({ citadelCount }: MolesCitadelTrackProps) {

  return (
    <div style={{ position: "relative", paddingTop: "6px" }}>
      <div
        style={{
          border: "1px solid var(--mantine-color-gray-3)",
          borderRadius: "8px",
          padding: "12px",
          backgroundColor: "white",
          boxShadow: "0 1px 3px rgba(0, 0, 0, 0.05)",
          position: "relative",
        }}
      >
        <Text
          size="xs"
          fw={700}
          c="dimmed"
          tt="uppercase"
          style={{
            position: "absolute",
            top: "-8px",
            left: "50%",
            transform: "translateX(-50%)",
            backgroundColor: "#f5ead6",
            paddingRight: "6px",
            paddingLeft: "6px",
          }}
        >
          Citadels
        </Text>

        <SimpleGrid cols={3} spacing="xs">
          {CITADEL_BONUSES.map((bonus, index) => {
            const isFilled = index < citadelCount;

            return (
              <Stack key={index} align="center" gap={4}>
                <Tooltip label={bonus} withArrow>
                  <Paper
                    w={60}
                    h={60}
                    withBorder
                    radius="md"
                    style={{
                      backgroundColor: isFilled
                        ? "#e8dcc4"
                        : "var(--mantine-color-gray-2)",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      borderColor: isFilled
                        ? "#d49d99"
                        : "var(--mantine-color-gray-4)",
                      cursor: "help",
                    }}
                  >
                    {isFilled ? (
                      <IconSwords
                        size={24}
                        color="#8B6F47"
                      />
                    ) : (
                      <Text size="xs" fw={700} c="dimmed">
                        {bonus}
                      </Text>
                    )}
                  </Paper>
                </Tooltip>
              </Stack>
            );
          })}
        </SimpleGrid>
      </div>
    </div>
  );
}
