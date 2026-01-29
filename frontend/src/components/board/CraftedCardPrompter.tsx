import { useContext } from "react";
import { GameContext } from "../../contexts/GameProvider";
import { UserContext } from "../../contexts/UserProvider";
import useCraftedCardsQuery from "../../hooks/useCraftedCardsQuery";
import useGetPlayersInfoQuery from "../../hooks/useGetPlayersInfoQuery";
import { Button, Group, Stack, Text, Paper, rem } from "@mantine/core";
import { GameActionContext } from "../../contexts/GameActionContext";

const CraftedCardPrompter = () => {
  const { gameId } = useContext(GameContext);
  const { username } = useContext(UserContext);
  const { players } = useGetPlayersInfoQuery(gameId);
  const { startActionOverride } = useContext(GameActionContext);

  const userPlayer = players?.find((p) => p.username === username);
  const factionStub = userPlayer?.faction || "";

  const { craftedCards } = useCraftedCardsQuery(gameId, factionStub);
  const usableCards = craftedCards?.filter((c) => c.can_be_used) || [];

  if (usableCards.length === 0) return null;

  return (
    <Paper
      withBorder
      p="sm"
      mb="md"
      shadow="xs"
      radius="md"
      style={{ width: "100%" }}
    >
      <Stack gap="xs">
        <Text
          fw={700}
          size="xs"
          c="dimmed"
          style={{ textTransform: "uppercase", letterSpacing: rem(1) }}
        >
          Usable Crafted Cards
        </Text>
        <Group>
          {usableCards.map((crafted, i) => (
            <Button
              key={i}
              variant="light"
              size="sm"
              color="blue"
              onClick={() => startActionOverride(crafted.action_endpoint!)}
            >
              Use {crafted.card.title}
            </Button>
          ))}
        </Group>
      </Stack>
    </Paper>
  );
};

export default CraftedCardPrompter;
