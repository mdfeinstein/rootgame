import { Box, Group, Paper, Stack, Text, ThemeIcon, Tooltip, Center } from "@mantine/core";
import { IconBomb, IconEye, IconLock, IconMapPin, IconCircleDot } from "@tabler/icons-react";

export const PLOT_ICONS: Record<string, any> = {
  Bomb: IconBomb,
  Snare: IconLock,
  Raid: IconMapPin,
  Extortion: IconEye,
};

interface CrowsPlotReserveProps {
  reservePlots: any[];
  totalCount: number;
  isOwner: boolean;
}

export default function CrowsPlotReserve({
  reservePlots,
  totalCount,
  isOwner,
}: CrowsPlotReserveProps) {
  const counts: Record<string, number> = {};
  reservePlots.forEach((p) => {
    if (!p.plot_type) return;
    // Map backend string (bomb, snare, etc) to display keys (Bomb, Snare, etc)
    const type = p.plot_type.charAt(0).toUpperCase() + p.plot_type.slice(1).toLowerCase();
    counts[type] = (counts[type] || 0) + 1;
  });

  return (
    <Paper p="xs" radius="md" withBorder shadow="sm" bg="white" style={{ flex: 1 }}>
      <Box mb={4}>
        <Text size="md" fw={800} ta="center" tt="uppercase" c="dimmed">
          Reserve Plots
        </Text>
      </Box>

      {isOwner ? (
        <Group justify="space-around">
          {Object.entries(PLOT_ICONS).map(([type, Icon]) => (
            <Tooltip key={type} label={type} withArrow position="bottom">
              <Stack gap={0} align="center">
                <ThemeIcon color="indigo" variant="light" size="lg">
                  <Icon size="1.2rem" />
                </ThemeIcon>
                <Text fw={700} size="sm">
                  {counts[type] || 0}
                </Text>
              </Stack>
            </Tooltip>
          ))}
        </Group>
      ) : (
        <Center h="100%" py="sm">
          <Group gap="xs">
            <ThemeIcon color="indigo" variant="light" size="xl">
              <IconCircleDot size="1.5rem" />
            </ThemeIcon>
            <Text fz={32} fw={900} c="indigo.8">
              {totalCount}
            </Text>
          </Group>
        </Center>
      )}
    </Paper>
  );
}
