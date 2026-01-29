import { Modal, SimpleGrid, Stack, Badge, Group, Text } from "@mantine/core";
import { GameCard } from "./Card";
import type { CraftedCardData } from "../../hooks/useCraftedCardsQuery";

interface CraftedCardModalProps {
  isOpen: boolean;
  onClose: () => void;
  craftedCards: CraftedCardData[] | undefined;
  factionLabel: string;
}

const CraftedCardModal = ({
  isOpen,
  onClose,
  craftedCards,
  factionLabel,
}: CraftedCardModalProps) => {
  return (
    <Modal
      opened={isOpen}
      onClose={onClose}
      title={`${factionLabel} - Crafted Cards`}
      size="xl"
    >
      <SimpleGrid cols={{ base: 1, sm: 2, md: 3 }} spacing="md">
        {craftedCards?.map((crafted, index) => (
          <Stack key={index} gap="xs" style={{ position: "relative" }}>
            <div style={{ height: "350px", position: "relative" }}>
              <GameCard
                cardData={crafted.card}
                isCollapsed={false}
                index={index}
              />
            </div>
            <Group justify="space-between" mt="md">
              <Badge color={crafted.used ? "red" : "green"}>
                {crafted.used ? "Used" : "Unused"}
              </Badge>
              {crafted.can_be_used && (
                <Badge color="blue" variant="filled">
                  Can be used now
                </Badge>
              )}
            </Group>
          </Stack>
        ))}
      </SimpleGrid>
      {(!craftedCards || craftedCards.length === 0) && (
        <Text c="dimmed" ta="center" py="xl">
          No crafted cards.
        </Text>
      )}
    </Modal>
  );
};

export default CraftedCardModal;
