import {
  Box,
  Group,
  Paper,
  Stack,
  Text,
  ThemeIcon,
  Modal,
  SimpleGrid,
  Card,
  Tooltip,
} from "@mantine/core";
import {
  IconTrophy,
  IconUsers,
  IconCircleDot,
  IconBomb,
  IconLock,
  IconMapPin,
  IconEye,
} from "@tabler/icons-react";

import { useContext } from "react";
import { GameContext } from "../../contexts/GameProvider";
import { useCrowPlayerQuery } from "../../hooks/useCrowPlayerQuery";

interface CrowsPlayerBoardProps {
  isOpen: boolean;
  onClose: () => void;
}

const PLOT_ICONS: Record<string, any> = {
  Bomb: IconBomb,
  Snare: IconLock,
  Raid: IconMapPin,
  Extortion: IconEye,
};

const PlotReserve = () => {
  const { gameId } = useContext(GameContext);
  const { privateInfo, isPrivateSuccess } = useCrowPlayerQuery(gameId);

  if (!isPrivateSuccess || !privateInfo) return null;

  const plots = privateInfo.reserve_plots;
  const counts: Record<string, number> = {};
  plots.forEach((p) => {
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
};

export default function CrowsPlayerBoard({
  isOpen,
  onClose,
}: CrowsPlayerBoardProps) {
  const { gameId } = useContext(GameContext);
  const { publicInfo, privateInfo } = useCrowPlayerQuery(gameId);

  if (!publicInfo) return null;

  const warriorsInSupply = publicInfo.warriors.filter(
    (w) => w.clearing_number === null,
  ).length;

  return (
    <Modal
      opened={isOpen}
      onClose={onClose}
      size="lg"
      centered
      title="Corvid Conspiracy Player Board"
    >
      <Paper
        p="md"
        radius="lg"
        style={{
          backgroundColor: "var(--mantine-color-indigo-0)",
          border: "2px solid var(--mantine-color-indigo-6)",
        }}
      >
        <Stack gap="xl">
          <Group justify="apart">
            <Group>
              <ThemeIcon color="indigo" size="xl" radius="md">
                <IconTrophy size="1.2rem" />
              </ThemeIcon>
              <Box>
                <Text size="xs" c="dimmed" fw={700} tt="uppercase">
                  Victory Points
                </Text>
                <Text size="xl" fw={900} c="indigo.9">
                  {publicInfo.player.score}
                </Text>
              </Box>
            </Group>
          </Group>

          <SimpleGrid cols={2} spacing="md">
            <Paper p="md" radius="md" withBorder>
              <Group>
                <ThemeIcon color="indigo" variant="light" size="lg">
                  <IconUsers size="1.2rem" />
                </ThemeIcon>
                <Box>
                  <Text size="xs" c="dimmed" fw={700} tt="uppercase">
                    Warriors in Supply
                  </Text>
                  <Text size="lg" fw={700}>
                    {warriorsInSupply}
                  </Text>
                </Box>
              </Group>
            </Paper>

            <Paper p="md" radius="md" withBorder>
              <Group>
                <ThemeIcon color="indigo" variant="light" size="lg">
                  <IconCircleDot size="1.2rem" />
                </ThemeIcon>
                <Box>
                  <Text size="xs" c="dimmed" fw={700} tt="uppercase">
                    Plots in Supply
                  </Text>
                  <Text size="lg" fw={700}>
                    {publicInfo.reserve_plots_count}
                  </Text>
                </Box>
              </Group>
            </Paper>
          </SimpleGrid>

          {privateInfo && <PlotReserve />}

          <Box>
            <Text fw={700} size="sm" mb="xs" c="indigo.8">
              Faction Abilities
            </Text>
            <Stack gap="xs">
              <Paper p="xs" radius="sm" bg="indigo.1">
                <Text size="sm" fw={600}>
                  Nimble
                </Text>
                <Text size="xs">
                  You can move regardless of who rules the origin or destination
                  clearing.
                </Text>
              </Paper>
              <Paper p="xs" radius="sm" bg="indigo.1">
                <Text size="sm" fw={600}>
                  Exposure
                </Text>
                <Text size="xs">
                  Other players can guess your facedown plots to remove them.
                </Text>
              </Paper>
            </Stack>
          </Box>
        </Stack>
      </Paper>
    </Modal>
  );
}
