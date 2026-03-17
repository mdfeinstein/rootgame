import { Group, Text, Tooltip, Stack, ThemeIcon } from "@mantine/core";
import { IconShieldCheck, IconCross, IconUsers } from "@tabler/icons-react";

interface CatHeaderSectionProps {
  warriorsInSupply: number;
}

export default function CatHeaderSection({ warriorsInSupply }: CatHeaderSectionProps) {
  return (
    <Group justify="space-between" align="center" px="md" mb="xs">
      <Stack gap={0}>
        <Text
          size="1.5rem"
          fw={900}
          variant="gradient"
          gradient={{ from: "orange.9", to: "orange.6", deg: 45 }}
          style={{ letterSpacing: "2px", fontFamily: "serif", lineHeight: 1 }}
        >
          Cats
        </Text>
        <Group gap={6} mt={4}>
          <ThemeIcon color="orange" variant="light" size="sm">
            <IconUsers size={14} />
          </ThemeIcon>
          <Text size="xs" fw={700} c="orange.9">
            {warriorsInSupply} WARRIORS IN SUPPLY
          </Text>
        </Group>
      </Stack>

      <Group gap="xl">
        <Tooltip
          label="Only you can place pieces in the clearing with the keep token."
          multiline
          w={220}
          withArrow
          position="bottom"
        >
          <Group gap={4} style={{ cursor: "help" }}>
            <IconShieldCheck
              size={20}
              color="var(--mantine-color-orange-7)"
            />
            <Text size="xs" fw={700} c="orange.8" tt="uppercase">
              The Keep
            </Text>
          </Group>
        </Tooltip>

        <Tooltip
          label="Whenever any Marquise warriors are removed, you may spend a card matching their clearing to place those warriors in the clearing with the keep token."
          multiline
          w={250}
          withArrow
          position="bottom"
        >
          <Group gap={4} style={{ cursor: "help" }}>
            <IconCross size={20} color="var(--mantine-color-orange-7)" />
            <Text size="xs" fw={700} c="orange.8" tt="uppercase">
              Field Hospitals
            </Text>
          </Group>
        </Tooltip>
      </Group>
    </Group>
  );
}
