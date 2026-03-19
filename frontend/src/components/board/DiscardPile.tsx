import {
  Modal,
  Button,
  ScrollArea,
  Text,
  Group,
  Stack,
  Paper,
  Box,
} from "@mantine/core";
import useDiscardPileQuery from "../../hooks/useDiscardPileQuery";
import { IconTrash } from "@tabler/icons-react";
import { GameCard } from "../cards/Card";

interface DiscardPileProps {
  gameId: number;
  isOpen: boolean;
  onToggle: () => void;
}

const DiscardPile: React.FC<DiscardPileProps> = ({
  gameId,
  isOpen,
  onToggle,
}) => {
  const { discardPile, isLoading } = useDiscardPileQuery(gameId);

  return (
    <>
      <Button
        variant="light"
        leftSection={<IconTrash size={16} />}
        onClick={onToggle}
        size="sm"
        color="gray"
      >
        Discard Pile
      </Button>

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
              Discard Pile
            </Text>
          </Group>
          <ScrollArea h={400} offsetScrollbars>
            <Stack gap="sm">
              {isLoading && <Text c="dimmed">Loading...</Text>}
              {!isLoading && (!discardPile || discardPile.length === 0) && (
                <Text c="dimmed" ta="center" mt="md">
                  The discard pile is empty.
                </Text>
              )}

              <Group gap="md" mt="md" justify="center" align="flex-start">
                {discardPile?.map((card, idx) => (
                  <Box key={idx}>
                    <GameCard
                      cardData={card}
                      isCollapsed={false}
                      index={idx}
                      isHand={false}
                    />
                  </Box>
                ))}
              </Group>
            </Stack>
          </ScrollArea>
        </Paper>
      </Modal>
    </>
  );
};

export default DiscardPile;
