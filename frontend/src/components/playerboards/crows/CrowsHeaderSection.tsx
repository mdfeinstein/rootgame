import { Group, Text, Tooltip, Stack, ThemeIcon } from "@mantine/core";
import {
  IconEye,
  IconShieldCheck,
  IconFeather,
  IconUsers,
} from "@tabler/icons-react";

interface CrowsHeaderSectionProps {
  warriorsInSupply: number;
}

export default function CrowsHeaderSection({
  warriorsInSupply,
}: CrowsHeaderSectionProps) {
  return (
    <Group justify="space-between" align="center" px="md" mb="xs">
      <Stack gap={0}>
        <Text
          size="1.5rem"
          fw={900}
          variant="gradient"
          gradient={{ from: "indigo.9", to: "indigo.6", deg: 45 }}
          style={{ letterSpacing: "2px", fontFamily: "serif", lineHeight: 1 }}
        >
          Crows
        </Text>
        <Group gap={6} mt={4}>
          <ThemeIcon color="indigo" variant="light" size="sm">
            <IconUsers size="0.8rem" />
          </ThemeIcon>
          <Text size="xs" fw={700} c="indigo.8">
            {warriorsInSupply} WARRIORS IN SUPPLY
          </Text>
        </Group>
      </Stack>

      <Group gap="lg">
        <Tooltip
          label="Anytime before drawing cards in their Evening, an enemy player in a clearing with a facedown plot token may show you a matching card to guess the type of plot token. If correct, they remove the plot and ignore its effect. If incorrect, you say 'no,' and they give you that card."
          multiline
          w={300}
          withArrow
          position="bottom"
        >
          <Group gap={4} style={{ cursor: "help" }}>
            <IconEye size={20} color="var(--mantine-color-indigo-7)" />
            <Text size="sm" fw={700} c="indigo.8">
              EXPOSURE
            </Text>
          </Group>
        </Tooltip>

        <Tooltip
          label="In battle as defender with a facedown plot token, you deal an extra hit."
          multiline
          w={220}
          withArrow
          position="bottom"
        >
          <Group gap={4} style={{ cursor: "help" }}>
            <IconShieldCheck size={20} color="var(--mantine-color-indigo-7)" />
            <Text size="sm" fw={700} c="indigo.8">
              AGENTS
            </Text>
          </Group>
        </Tooltip>

        <Tooltip
          label="You can move regardless of who rules your clearing."
          multiline
          w={200}
          withArrow
          position="bottom"
        >
          <Group gap={4} style={{ cursor: "help" }}>
            <IconFeather size={20} color="var(--mantine-color-indigo-7)" />
            <Text size="sm" fw={700} c="indigo.8">
              NIMBLE
            </Text>
          </Group>
        </Tooltip>
      </Group>
    </Group>
  );
}
