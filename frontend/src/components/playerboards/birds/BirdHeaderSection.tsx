import { Group, Paper, Stack, Text, Tooltip, rem, ThemeIcon } from "@mantine/core";
import { IconCrown, IconCoins, IconUsers } from "@tabler/icons-react";

export type Leader = "Builder" | "Charismatic" | "Commander" | "Despot";
export const leaderTextMapper: Record<Leader, string> = {
  Builder:
    "Whenever you craft, you ignore your Disdain for Trade special ability",
  Charismatic:
    "Whenever you take a Recruit action, you must place two warriors instead of one.",
  Commander: "In battle as attacker, you deal an extra hit.",
  Despot:
    "Whenever you remove at least one enemy building or token in battle, you score one extra victory point",
};

interface BirdHeaderSectionProps {
  activeLeader: any;
  warriorsInSupply: number;
}

export default function BirdHeaderSection({
  activeLeader,
  warriorsInSupply,
}: BirdHeaderSectionProps) {
  return (
    <Group justify="space-between" align="center" px="md" mb="xs">
      <Stack gap={0}>
        <Text
          size="1.5rem"
          fw={900}
          variant="gradient"
          gradient={{ from: "blue.9", to: "blue.6", deg: 45 }}
          style={{ letterSpacing: "2px", fontFamily: "serif", lineHeight: 1 }}
        >
          Eyrie Dynasties
        </Text>
        <Group gap={6} mt={4}>
          <ThemeIcon color="blue" variant="light" size="sm">
            <IconUsers size={14} />
          </ThemeIcon>
          <Text size="xs" fw={700} c="blue.9">
            {warriorsInSupply} WARRIORS IN SUPPLY
          </Text>
        </Group>
      </Stack>

      <Group gap="xl">
        <Tooltip
          label="You rule any clearings where you are tied in presence."
          multiline
          w={220}
          withArrow
          position="bottom"
        >
          <Group gap={4} style={{ cursor: "help" }}>
            <IconCrown size={20} color="var(--mantine-color-blue-7)" />
            <Text size="xs" fw={700} c="blue.8" tt="uppercase">
              Lords of the Forest
            </Text>
          </Group>
        </Tooltip>

        <Tooltip
          label="When crafting items, you score only +1 victory point."
          multiline
          w={250}
          withArrow
          position="bottom"
        >
          <Group gap={4} style={{ cursor: "help" }}>
            <IconCoins size={20} color="var(--mantine-color-blue-7)" />
            <Text size="xs" fw={700} c="blue.8" tt="uppercase">
              Disdain for Trade
            </Text>
          </Group>
        </Tooltip>
      </Group>

      {activeLeader ? (
        <Tooltip
          label={leaderTextMapper[activeLeader.leader_display as Leader] || ""}
          multiline
          w={220}
          withArrow
          position="bottom"
          transitionProps={{ duration: 200, transition: "fade" }}
        >
          <Paper
            withBorder
            px="md"
            py={4}
            radius="sm"
            style={{
              borderColor: "var(--mantine-color-blue-6)",
              backgroundColor: "var(--mantine-color-blue-6)",
              color: "white",
              cursor: "help",
            }}
          >
            <Stack gap={0} align="center">
              <Text
                size="10px"
                tt="uppercase"
                fw={800}
                style={{ letterSpacing: rem(0.5) }}
              >
                Current Leader
              </Text>
              <Text size="md" fw={900}>
                {activeLeader.leader_display.toUpperCase()}
              </Text>
            </Stack>
          </Paper>
        </Tooltip>
      ) : (
        <Paper
          withBorder
          px="md"
          py={4}
          radius="sm"
          style={{
            borderColor: "var(--mantine-color-gray-4)",
            backgroundColor: "var(--mantine-color-gray-1)",
          }}
        >
          <Text size="sm" c="dimmed" fw={700} fs="italic">
            No Active Leader
          </Text>
        </Paper>
      )}
    </Group>
  );
}
