import {
  Modal,
  ScrollArea,
  Text,
  Group,
  Stack,
  Paper,
  Tooltip,
  ActionIcon,
} from "@mantine/core";
import {
  IconShoe,
  IconBriefcase,
  IconCrosshair,
  IconHammer,
  IconSword,
  IconCoffee,
  IconCoin,
  IconTools,
} from "@tabler/icons-react";
import useCraftableItemsQuery from "../../hooks/useCraftableItemsQuery";
import type { CraftableItemType } from "../../hooks/useCraftableItemsQuery";

interface CraftableItemsProps {
  gameId: number;
  isOpen: boolean;
  onToggle: () => void;
}

const getItemIcon = (item: CraftableItemType) => {
  switch (item.item.label) {
    case "Boots": // BOOTS
      return <IconShoe size={36} color="#5c5c5c" />;
    case "Bag": // BAG
      return <IconBriefcase size={36} color="#5c5c5c" />;
    case "Crossbow": // CROSSBOW
      return <IconCrosshair size={36} color="#333" />;
    case "Hammer": // HAMMER
      return <IconHammer size={36} color="#4a4a4a" />;
    case "Sword": // SWORD
      return <IconSword size={36} color="#b0b0b0" />;
    case "Tea": // TEA
      return <IconCoffee size={36} color="#7a5c40" />;
    case "Coin": // COIN
      return <IconCoin size={36} color="#d4af37" />;
    default:
      return <IconTools size={36} color="black" />;
  }
};

const CraftableItems: React.FC<CraftableItemsProps> = ({
  gameId,
  isOpen,
  onToggle,
}) => {
  const { craftableItems, isLoading } = useCraftableItemsQuery(gameId);

  return (
    <>
      <Tooltip label="Available Craftable Items" withArrow position="bottom" zIndex={2000}>
        <ActionIcon
          variant="light"
          onClick={onToggle}
          w={64}
          h={48}
          color="teal"
          radius="md"
        >
          <IconTools size={28} />
        </ActionIcon>
      </Tooltip>

      <Modal
        opened={isOpen}
        onClose={onToggle}
        size="lg"
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
              Available Craftable Items
            </Text>
          </Group>
          <ScrollArea h={300} offsetScrollbars>
            <Stack gap="sm">
              {isLoading && <Text c="dimmed">Loading...</Text>}
              {!isLoading &&
                (!craftableItems || craftableItems.length === 0) && (
                  <Text c="dimmed" ta="center" mt="md">
                    No craftable items remaining in the supply.
                  </Text>
                )}

              <Group gap="lg" mt="md" justify="center" align="flex-start">
                {craftableItems?.map((craftable, idx) => (
                  <Tooltip
                    key={idx}
                    label={craftable.item.label}
                    withArrow
                    position="top"
                  >
                    <Paper
                      p="md"
                      withBorder
                      shadow="xs"
                      radius="md"
                      style={{
                        backgroundColor: "white",
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                        cursor: "help",
                        transition: "transform 0.1s ease",
                      }}
                      onMouseEnter={(e) => {
                        e.currentTarget.style.transform = "scale(1.1)";
                      }}
                      onMouseLeave={(e) => {
                        e.currentTarget.style.transform = "scale(1)";
                      }}
                    >
                      {getItemIcon(craftable)}
                    </Paper>
                  </Tooltip>
                ))}
              </Group>
            </Stack>
          </ScrollArea>
        </Paper>
      </Modal>
    </>
  );
};

export default CraftableItems;
