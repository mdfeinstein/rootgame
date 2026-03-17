import { Group, Stack, Text, Tooltip, ThemeIcon } from "@mantine/core";
import { IconShieldCheck, IconHandStop, IconUsers } from "@tabler/icons-react";

interface WaHeaderSectionProps {
  warriorsInSupply: number;
}

export default function WaHeaderSection({
  warriorsInSupply,
}: WaHeaderSectionProps) {
  return (
    <Group justify="space-between" align="center" px="md" mb="xs">
      <Stack gap={0}>
        <Text
          size="1.5rem"
          fw={900}
          variant="gradient"
          gradient={{ from: "green.9", to: "green.6", deg: 45 }}
          style={{ letterSpacing: "2px", fontFamily: "serif", lineHeight: 1 }}
        >
          Woodland Alliance
        </Text>
        <Group gap={6} mt={4}>
          <ThemeIcon color="green" variant="light" size="sm">
            <IconUsers size={14} />
          </ThemeIcon>
          <Text size="xs" fw={700} c="green.9">
            {warriorsInSupply} WARRIORS IN SUPPLY
          </Text>
        </Group>
      </Stack>

      <Group gap="lg">
        <Tooltip
          label="When a player removes sympathy or moves any warriors into a sympathetic clearing, they must add a matching card from their hand to your supporters. If they cannot, they show you their hand, and you draw a card and add it to your supporters."
          multiline
          w={300}
          withArrow
          position="bottom"
        >
          <Group gap={4} style={{ cursor: "help" }}>
            <IconHandStop size={20} color="var(--mantine-color-green-7)" />
            <Text size="sm" fw={700} c="green.8">
              OUTRAGE
            </Text>
          </Group>
        </Tooltip>

        <Tooltip
          label="In battle as defender, you use the higher roll and the attacker uses the lower."
          multiline
          w={220}
          withArrow
          position="bottom"
        >
          <Group gap={4} style={{ cursor: "help" }}>
            <IconShieldCheck size={20} color="var(--mantine-color-green-7)" />
            <Text size="sm" fw={700} c="green.8">
              GUERRILLA WAR
            </Text>
          </Group>
        </Tooltip>
      </Group>
    </Group>
  );
}
