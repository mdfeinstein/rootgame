import { ActionIcon, Group, Paper, Text, Tooltip, Stack } from "@mantine/core";
import { useContext } from "react";
import { useDominanceSupplyQuery } from "../../hooks/useDominanceSupplyQuery";
import { GameContext } from "../../contexts/GameProvider";
import { GameActionContext } from "../../contexts/GameActionContext";
import { SUIT_CONFIG } from "../cards/Card";
import type { CardType } from "../../hooks/useGetPlayerHandQuery";

const DominanceSupply = () => {
  const { gameId } = useContext(GameContext);
  const { data: dominanceSupply } = useDominanceSupplyQuery(gameId);
  const { startActionOverride } = useContext(GameActionContext);

  if (!dominanceSupply || dominanceSupply.length === 0) {
    return null;
  }

  const handleSwapClick = () => {
    startActionOverride("/api/action/dominance/swap/");
  };

  return (
    <Paper withBorder p="xs" radius="md" shadow="sm">
      <Stack gap="xs">
        <Text size="xs" c="dimmed" fw={700}>
          DOMINANCE SUPPLY
        </Text>
        <Group gap="xs">
          {dominanceSupply.map((entry: { card: CardType }) => {
            const card = entry.card;
            const config = SUIT_CONFIG[card.suit as keyof typeof SUIT_CONFIG];
            const Icon = config?.icon;
            return (
              <Tooltip
                key={card.card_name}
                label={`Click to Swap for ${card.suit_name} Dominance`}
              >
                <ActionIcon
                  variant="light"
                  color={config?.color || "gray"}
                  size="lg"
                  onClick={handleSwapClick}
                  style={{ border: "1px solid" }}
                >
                  {Icon && <Icon size={20} />}
                </ActionIcon>
              </Tooltip>
            );
          })}
        </Group>
      </Stack>
    </Paper>
  );
};

export default DominanceSupply;
