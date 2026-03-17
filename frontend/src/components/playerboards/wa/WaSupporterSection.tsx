import {
  Box,
  Card,
  Center,
  Group,
  Paper,
  Stack,
  Text,
  ThemeIcon,
  Tooltip,
} from "@mantine/core";
import { IconCards } from "@tabler/icons-react";
import { SUIT_CONFIG } from "../../../data/suitConfig";
import type { CardType } from "../../../hooks/useGetPlayerHandQuery";

interface SupporterStackProps {
  supporterCards: CardType[];
}

const SupporterStack = ({ supporterCards }: SupporterStackProps) => {
  const counts = {
    fox: supporterCards.filter((c) => c.suit.value === "r").length,
    rabbit: supporterCards.filter((c) => c.suit.value === "y").length,
    mouse: supporterCards.filter((c) => c.suit.value === "o").length,
    bird: supporterCards.filter((c) => c.suit.value === "b").length,
  };

  return (
    <Card shadow="sm" radius="md" withBorder p="xs" mt="md" w="100%">
      <Text size="sm" fw={700} ta="center" mb="xs">
        Supporter Stack
      </Text>
      <Group justify="space-around">
        <Stack gap={0} align="center">
          <ThemeIcon color="red" variant="light" size="lg">
            <SUIT_CONFIG.r.icon size="1.2rem" />
          </ThemeIcon>
          <Text fw={700}>{counts.fox}</Text>
        </Stack>
        <Stack gap={0} align="center">
          <ThemeIcon color="yellow" variant="light" size="lg">
            <SUIT_CONFIG.y.icon size="1.2rem" />
          </ThemeIcon>
          <Text fw={700}>{counts.rabbit}</Text>
        </Stack>
        <Stack gap={0} align="center">
          <ThemeIcon color="orange" variant="light" size="lg">
            <SUIT_CONFIG.o.icon size="1.2rem" />
          </ThemeIcon>
          <Text fw={700}>{counts.mouse}</Text>
        </Stack>
        <Stack gap={0} align="center">
          <ThemeIcon color="blue" variant="light" size="lg">
            <SUIT_CONFIG.b.icon size="1.2rem" />
          </ThemeIcon>
          <Text fw={700}>{counts.bird}</Text>
        </Stack>
      </Group>
    </Card>
  );
};

interface WaSupporterSectionProps {
  supporterCount: number;
  playerIsWA: boolean;
  supporterCards?: CardType[];
}

export default function WaSupporterSection({
  supporterCount,
  playerIsWA,
  supporterCards,
}: WaSupporterSectionProps) {
  return (
    <Paper
      radius="md"
      withBorder
      shadow="sm"
      style={{
        backgroundColor: "white",
        display: "flex",
        flexDirection: "column",
        padding: "0.5rem",
        flex: 1,
      }}
    >
      <Box mb={4}>
        <Tooltip
          label="If you have no bases on the map, discard any cards that would be added beyond 5."
          multiline
          w={220}
          withArrow
          position="bottom"
        >
          <Text
            size="md"
            fw={800}
            ta="center"
            tt="uppercase"
            c="dimmed"
            style={{ cursor: "help" }}
          >
            Supporters
          </Text>
        </Tooltip>
      </Box>

      <Center style={{ flex: 1 }}>
        <Stack align="center" gap={0}>
          <IconCards size={48} color="var(--mantine-color-green-7)" />
          <Text fz={36} fw={900} lh={1} c="green.9">
            {supporterCount}
          </Text>
        </Stack>
      </Center>

      {playerIsWA && supporterCards && (
        <SupporterStack supporterCards={supporterCards} />
      )}
    </Paper>
  );
}
