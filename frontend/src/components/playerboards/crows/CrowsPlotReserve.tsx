import { Card, Group, Stack, Text, ThemeIcon, Tooltip } from "@mantine/core";
import { IconBomb, IconEye, IconLock, IconMapPin } from "@tabler/icons-react";

export const PLOT_ICONS: Record<string, any> = {
  Bomb: IconBomb,
  Snare: IconLock,
  Raid: IconMapPin,
  Extortion: IconEye,
};

interface CrowsPlotReserveProps {
  reservePlots: any[];
}

export default function CrowsPlotReserve({
  reservePlots,
}: CrowsPlotReserveProps) {
  const counts: Record<string, number> = {};
  reservePlots.forEach((p) => {
    const type = p.plot_type.charAt(0).toUpperCase() + p.plot_type.slice(1);
    counts[type] = (counts[type] || 0) + 1;
  });

  return (
    <Card shadow="sm" radius="md" withBorder p="xs" mt="md" w="100%">
      <Text size="sm" fw={700} ta="center" mb="xs">
        Reserve Plots
      </Text>
      <Group justify="space-around">
        {Object.entries(PLOT_ICONS).map(([type, Icon]) => (
          <Tooltip key={type} label={type} withArrow>
            <Stack gap={0} align="center">
              <ThemeIcon color="indigo" variant="light" size="lg">
                <Icon size="1.2rem" />
              </ThemeIcon>
              <Text fw={700}>{counts[type] || 0}</Text>
            </Stack>
          </Tooltip>
        ))}
      </Group>
    </Card>
  );
}
