import { useContext, useState } from "react";
import type { CardType } from "../../hooks/useGetPlayerHandQuery";
import { GameActionContext } from "../../contexts/GameActionContext";
import { GameContext } from "../../contexts/GameProvider";
import useGetPlayersInfoQuery from "../../hooks/useGetPlayersInfoQuery";
import { UserContext } from "../../contexts/UserProvider";
import {
  IconMickey,
  IconBrandFirefox, // Using Flame for Fox/Red
  IconCarrot, // Using Carrot for Rabbit/Yellow
  IconFeather, // Using Bird/Blue
} from "@tabler/icons-react";

export const SUIT_CONFIG = {
  o: { color: "orange.6", icon: IconMickey, label: "Mouse" },
  r: { color: "red.7", icon: IconBrandFirefox, label: "Fox" },
  y: { color: "yellow.5", icon: IconCarrot, label: "Rabbit" },
  b: { color: "blue.6", icon: IconFeather, label: "Bird" },
};

const label_to_suit = {
  Mouse: "o",
  Fox: "r",
  Rabbit: "y",
  Bird: "b",
};

import {
  Badge,
  Box,
  Divider,
  Group,
  Stack,
  Text,
  rem,
  Button,
} from "@mantine/core";

export const GameCard = ({
  cardData,
  isCollapsed,
  index,
}: {
  cardData: CardType;
  isCollapsed: boolean;
  index: number;
}) => {
  const config = SUIT_CONFIG[cardData.suit];
  const Icon = config.icon;
  const [isHovered, setIsHovered] = useState(false);
  const { submitPayloadCallback, startActionOverride } =
    useContext(GameActionContext);
  const { gameId } = useContext(GameContext);
  const { username } = useContext(UserContext);
  const { players } = useGetPlayersInfoQuery(gameId);
  const currentPlayer = players?.find((p) => p.username === username);

  const submitPayloadOnClick = () => {
    submitPayloadCallback({ card: cardData.card_name });
  };

  const handleActivateDominance = (e: React.MouseEvent) => {
    e.stopPropagation();
    startActionOverride("/api/action/dominance/activate/");
  };

  const map_suit_to_color = (suit: string) => {
    return SUIT_CONFIG[suit as keyof typeof SUIT_CONFIG]?.color || "gray";
  };

  const canActivate =
    cardData.dominance &&
    (currentPlayer?.score || 0) >= 10 &&
    !currentPlayer?.active_dominance;

  return (
    <Box
      w={250}
      pos="absolute"
      bottom={0}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
      onClick={() => submitPayloadOnClick()}
      style={{
        borderRadius: "8px 8px 0 0",
        overflow: "hidden",
        border: "1px solid #dee2e6",
        backgroundColor: "#fff",
        cursor: "pointer",
        transition: "transform 0.2s ease",
        zIndex: isHovered ? 100 : index,
        // transform: isHovered ? "translateY(-20%)" : "translateY(0%)",
      }}
    >
      {/* Top Bar */}
      <Group
        bg={config.color}
        px="sm"
        py={rem(4)}
        gap="xs"
        wrap="nowrap"
        style={{ color: "white" }}
      >
        <Icon size={50} />
        <Text
          fw={700}
          size="sm"
          // truncate
          style={{ letterSpacing: rem(0.5), textTransform: "uppercase" }}
        >
          {cardData.title}
        </Text>
      </Group>

      {/* Placeholder for expanded content */}
      {!isCollapsed && (
        <Stack p="sm" gap="xs">
          Crafting Cost
          {/* Crafting Section */}
          {cardData.craftable && (
            <Group justify="space-between" align="flex-start">
              <Group gap={4}>
                {cardData.cost?.map((label, i) => {
                  const s = label_to_suit[label];
                  const CostIcon =
                    SUIT_CONFIG[s as keyof typeof SUIT_CONFIG].icon;
                  return (
                    <Box
                      key={i}
                      c={SUIT_CONFIG[s as keyof typeof SUIT_CONFIG].color}
                    >
                      <CostIcon size={50} />
                    </Box>
                  );
                })}
              </Group>
            </Group>
          )}
          <Divider label="Effect" labelPosition="left" />
          {/* Main Card Text */}
          <Text
            size="sm"
            lh={1.4}
            style={{ fontStyle: cardData.ambush ? "italic" : "normal" }}
          >
            {cardData.text}
          </Text>
          {/* Item Section */}
          {cardData.item && (
            <Box
              mt="xs"
              p={rem(4)}
              style={{
                backgroundColor: "#f8f9fa",
                borderRadius: rem(4),
                border: "1px dashed #ced4da",
              }}
            >
              <Text size="xs" fw={700} c="dimmed" ta="center">
                ITEM: {cardData.item_name}
              </Text>
              {cardData.crafted_points > 0 && (
                <Badge variant="filled" color="yellow.8" radius="sm">
                  +{cardData.crafted_points} VP
                </Badge>
              )}
            </Box>
          )}
          {/* Special Labels */}
          <Group gap={5}>
            {cardData.ambush && (
              <Badge size="xs" color="dark">
                Ambush
              </Badge>
            )}
            {cardData.dominance && (
              <Badge size="xs" color="blue">
                Dominance
              </Badge>
            )}
            {canActivate && (
              <Button
                size="xs"
                color={map_suit_to_color(cardData.suit)}
                onClick={handleActivateDominance}
              >
                Activate
              </Button>
            )}
          </Group>
        </Stack>
      )}
    </Box>
  );
};

const Card = ({ cardData }: { cardData: CardType }) => {
  const { submitPayloadCallback } = useContext(GameActionContext);
  const submitPayloadOnClick = () => {
    submitPayloadCallback({ card: cardData.card_name });
  };
  const colormap = {
    r: "red",
    y: "yellow",
    o: "orange",
    b: "blue",
  };
  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        width: "100%",
        height: "100%",
        background: "#00000095",
      }}
      onClick={() => submitPayloadOnClick()}
    >
      <div style={{ color: colormap[cardData.suit] }}>{cardData.suit}</div>
      <div>{cardData.title}</div>
      <div>{cardData.text}</div>
      <div>{cardData.cost}</div>
      {/* <div>{cardData.craftable}</div>
      <div>{cardData.item}</div>
      <div>{cardData.craftedPoints}</div>
      <div>{cardData.ambush}</div>
      <div>{cardData.dominance}</div> */}
    </div>
  );
};

export default Card;
