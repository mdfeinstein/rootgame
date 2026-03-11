import { Group, Paper, Stack, Text, ThemeIcon, Tooltip } from "@mantine/core";

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
}

export default function BirdHeaderSection({
  activeLeader,
}: BirdHeaderSectionProps) {
  return (
    <Paper
      p="md"
      radius="md"
      withBorder
      style={{
        borderColor: "var(--mantine-color-blue-6)",
        backgroundColor: "var(--mantine-color-blue-0)",
      }}
    >
      <Group justify="space-between" align="center">
        <Group>
          <ThemeIcon size="xl" radius="md" color="blue" variant="filled">
            <Text fw={900} size="lg">
              B
            </Text>
          </ThemeIcon>
          <Stack gap={0}>
            <Text size="lg" fw={900} tt="uppercase" c="blue.9">
              Birds
            </Text>
          </Stack>
        </Group>

        {activeLeader ? (
          <Tooltip
            label={
              leaderTextMapper[activeLeader.leader_display as Leader] || ""
            }
            multiline
            w={220}
            withArrow
            transitionProps={{ duration: 200, transition: "fade" }}
          >
            <Group>
              <Stack gap={0} align="flex-end">
                <Text size="xs" c="dimmed" tt="uppercase" fw={700}>
                  Current Leader
                </Text>
                <Text size="lg" fw={800} c="blue.9">
                  {activeLeader.leader_display}
                </Text>
              </Stack>
            </Group>
          </Tooltip>
        ) : (
          <Text c="dimmed" fs="italic">
            No Active Leader
          </Text>
        )}
      </Group>
    </Paper>
  );
}
