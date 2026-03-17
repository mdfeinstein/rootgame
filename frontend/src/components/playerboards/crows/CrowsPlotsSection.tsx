import { Group, Paper, Stack, Text, Tooltip, ThemeIcon } from "@mantine/core";
import { PLOT_ICONS } from "./CrowsPlotReserve";

const PLOTS_INFO = [
  {
    type: "Bomb",
    description: "When flipped, remove all enemy pieces in its clearing, then remove this token.",
  },
  {
    type: "Snare",
    description: "While face up, enemy pieces cannot be placed in or moved from its clearing.",
  },
  {
    type: "Extortion",
    description: "When flipped, take a random card from each player who has any pieces in its clearing. While face up, you draw an extra card in Evening.",
  },
  {
    type: "Raid",
    description: "When removed, place one warrior in each adjacent clearing. (Exposure doesn't trigger this.)",
  },
];

export default function CrowsPlotsSection() {
  return (
    <Paper p="xs" radius="md" withBorder shadow="sm" bg="white">
      <Text size="md" fw={800} ta="center" mb={8} tt="uppercase" c="dimmed">
        Plot Tokens
      </Text>
      <Stack gap={8}>
        {PLOTS_INFO.map((plot) => {
          const Icon = PLOT_ICONS[plot.type];
          return (
            <Tooltip
              key={plot.type}
              label={plot.description}
              multiline
              w={250}
              withArrow
              position="left"
            >
              <Group gap="xs" style={{ cursor: "help" }}>
                <ThemeIcon variant="light" color="indigo" size="md">
                  <Icon size="1rem" />
                </ThemeIcon>
                <Text size="sm" fw={700}>
                  {plot.type}
                </Text>
              </Group>
            </Tooltip>
          );
        })}
      </Stack>
    </Paper>
  );
}
