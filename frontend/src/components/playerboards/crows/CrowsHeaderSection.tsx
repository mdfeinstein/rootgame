import { Box, Group, Paper, SimpleGrid, Text, ThemeIcon } from "@mantine/core";
import { IconCircleDot, IconTrophy, IconUsers } from "@tabler/icons-react";

interface CrowsHeaderSectionProps {
  score: number;
  warriorsInSupply: number;
  plotsInSupply: number;
}

export default function CrowsHeaderSection({
  score,
  warriorsInSupply,
  plotsInSupply,
}: CrowsHeaderSectionProps) {
  return (
    <>
      <Group justify="space-between">
        <Group>
          <ThemeIcon color="indigo" size="xl" radius="md">
            <IconTrophy size="1.2rem" />
          </ThemeIcon>
          <Box>
            <Text size="xs" c="dimmed" fw={700} tt="uppercase">
              Victory Points
            </Text>
            <Text size="xl" fw={900} c="indigo.9">
              {score}
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
                {plotsInSupply}
              </Text>
            </Box>
          </Group>
        </Paper>
      </SimpleGrid>
    </>
  );
}
