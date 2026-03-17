import { Group, Stack, Text, Tooltip, Paper } from "@mantine/core";
import { IconShieldCheck, IconCross } from "@tabler/icons-react";

export default function CatSpecialAbilities() {
  return (
    <Paper
      radius="md"
      p="xs"
      bg="orange.0"
      withBorder
      style={{ borderColor: "var(--mantine-color-orange-3)" }}
    >
      <Stack gap="xs">
        <Text
          fw={700}
          size="sm"
          c="orange.9"
          tt="uppercase"
          style={{ letterSpacing: "1px" }}
        >
          Special Abilities
        </Text>
        <Group gap="5rem" justify="left">
          <Tooltip
            label="Only you can place pieces in the clearing with the keep token."
            multiline
            w={220}
            withArrow
          >
            <Group gap={4} style={{ cursor: "help" }}>
              <IconShieldCheck
                size={18}
                color="var(--mantine-color-orange-7)"
              />
              <Text size="sm" fw={600} c="orange.8">
                The Keep
              </Text>
            </Group>
          </Tooltip>

          <Tooltip
            label="Whenever any Marquise warriors are removed, you may spend a card matching their clearing to place those warriors in the clearing with the keep token."
            multiline
            w={250}
            withArrow
          >
            <Group gap={4} style={{ cursor: "help" }}>
              <IconCross size={18} color="var(--mantine-color-orange-7)" />
              <Text size="sm" fw={600} c="orange.8">
                Field Hospitals
              </Text>
            </Group>
          </Tooltip>
        </Group>
      </Stack>
    </Paper>
  );
}
