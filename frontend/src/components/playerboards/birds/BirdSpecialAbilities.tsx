import { Group, Stack, Text, Tooltip, Paper } from "@mantine/core";
import { IconCrown, IconCoins } from "@tabler/icons-react";

export default function BirdSpecialAbilities() {
  return (
    <Paper
      radius="md"
      p="xs"
      bg="blue.0"
      withBorder
      style={{ borderColor: "var(--mantine-color-blue-3)" }}
    >
      <Stack gap="xs">
        <Text
          fw={700}
          size="sm"
          c="blue.9"
          tt="uppercase"
          style={{ letterSpacing: "1px" }}
        >
          Special Abilities
        </Text>
        <Group gap="xl" justify="space-between">
          <Tooltip
            label="You rule any clearings where you are tied in presence."
            multiline
            w={220}
            withArrow
          >
            <Group gap={4} style={{ cursor: "help" }}>
              <IconCrown size={18} color="var(--mantine-color-blue-7)" />
              <Text size="sm" fw={600} c="blue.8">
                Lords of the Forest
              </Text>
            </Group>
          </Tooltip>

          <Tooltip
            label="When crafting items, you score only +1 victory point."
            multiline
            w={250}
            withArrow
          >
            <Group gap={4} style={{ cursor: "help" }}>
              <IconCoins size={18} color="var(--mantine-color-blue-7)" />
              <Text size="sm" fw={600} c="blue.8">
                Disdain for Trade
              </Text>
            </Group>
          </Tooltip>
        </Group>
      </Stack>
    </Paper>
  );
}
