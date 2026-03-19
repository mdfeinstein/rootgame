import {
  Modal,
  Button,
  ScrollArea,
  Card as MantineCard,
  Text,
  Badge,
  Group,
  Stack,
  Indicator,
  Paper,
  Box,
} from "@mantine/core";
import useRevealedCardsQuery from "../../hooks/useRevealedCardsQuery";
import { IconCards } from "@tabler/icons-react";

import { GameCard } from "../cards/Card";

interface RevealedCardsHistoryProps {
  gameId: number;
  isOpen: boolean;
  onToggle: () => void;
}

const RevealedCardsHistory: React.FC<RevealedCardsHistoryProps> = ({
  gameId,
  isOpen,
  onToggle,
}) => {
  const { revealedCards, isLoading } = useRevealedCardsQuery(gameId);

  // Consider an item new if turns_ago is 0, just to highlight
  const hasRecentReveals =
    revealedCards?.some((rc) => rc.turns_ago === 0) ?? false;

  const groupedCards = revealedCards?.reduce(
    (acc, rc) => {
      const key = `${rc.turns_ago}-${rc.event_type}-${rc.faction.value}`;
      if (!acc[key]) {
        acc[key] = {
          turns_ago: rc.turns_ago,
          event_type: rc.event_type,
          faction: rc.faction,
          cards: [],
        };
      }
      
      // Deduplicate cards in the same event based on card id
      if (!acc[key].cards.some((c: any) => c.id === rc.card.id)) {
        acc[key].cards.push(rc.card);
      }
      
      return acc;
    },
    {} as Record<
      string,
      { turns_ago: number; event_type: string; faction: any; cards: any[] }
    >
  ) || {};

  const sortedGroups = Object.values(groupedCards).sort(
    (a, b) => a.turns_ago - b.turns_ago
  );

  return (
    <>
      <Indicator
        disabled={!hasRecentReveals}
        color="red"
        size={12}
        offset={4}
        withBorder
      >
        <Button
          variant="light"
          leftSection={<IconCards size={16} />}
          onClick={onToggle}
          size="sm"
        >
          Revealed Cards
        </Button>
      </Indicator>

      <Modal
        opened={isOpen}
        onClose={onToggle}
        size="80%"
        centered
        padding={0}
        withCloseButton={false}
        styles={{ content: { background: "transparent", boxShadow: "none" } }}
        overlayProps={{ opacity: 0.5, blur: 4 }}
      >
        <Paper
          p="md"
          radius="lg"
          shadow="xl"
          style={{
            backgroundColor: "#fef6e4", // Warm paper-like background
            border: "4px solid var(--mantine-color-gray-6)",
            overflow: "hidden",
            position: "relative",
          }}
        >
          <Group justify="center" mb="md">
            <Text size="xl" fw={700}>
              Revealed Cards History
            </Text>
          </Group>
          <ScrollArea h={400} offsetScrollbars>
            <Stack gap="sm">
              {isLoading && <Text c="dimmed">Loading...</Text>}
              {!isLoading && (!revealedCards || revealedCards.length === 0) && (
                <Text c="dimmed" ta="center" mt="md">
                  No cards have been revealed to you yet.
                </Text>
              )}
              {sortedGroups.map((group, idx) => (
                <MantineCard key={idx} shadow="sm" padding="md" radius="md" withBorder>
                  <Group justify="space-between" mb="xs">
                    <Group gap="xs">
                      <Badge color="blue" variant="light" size="lg">
                        {group.event_type}
                      </Badge>
                      <Text fw={500}>by {group.faction.label}</Text>
                    </Group>
                    <Text size="sm" c="dimmed" fw={600}>
                      {group.turns_ago === 0 ? "This turn" : `${group.turns_ago} turn(s) ago`}
                    </Text>
                  </Group>

                  <Group gap="md" mt="md" align="flex-start">
                    {group.cards.map((card, cidx) => (
                      <Box key={cidx}>
                        <GameCard
                          cardData={card}
                          isCollapsed={false}
                          index={cidx}
                          isHand={false}
                        />
                      </Box>
                    ))}
                  </Group>
                </MantineCard>
              ))}
            </Stack>
          </ScrollArea>
        </Paper>
      </Modal>
    </>
  );
};

export default RevealedCardsHistory;
