import { useContext, useState } from "react";
import type { CardType } from "../../hooks/useGetPlayerHandQuery";
import { GameActionContext } from "../../contexts/GameActionProvider";
import { GameContext } from "../../contexts/GameProvider";
import useGetPlayersInfoQuery from "../../hooks/useGetPlayersInfoQuery";
import { UserContext } from "../../contexts/UserProvider";

import { SUIT_CONFIG } from "../../data/suitConfig";
import type { SuitValue } from "../../data/suitConfig";

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
  isHand = true,
}: {
  cardData: CardType;
  isCollapsed: boolean;
  index: number;
  isHand?: boolean;
}) => {
  const config = SUIT_CONFIG[cardData.suit.value as SuitValue];
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
    return SUIT_CONFIG[suit as SuitValue]?.color || "gray";
  };

  const canActivate =
    isHand &&
    cardData.dominance &&
    (currentPlayer?.score || 0) >= 10 &&
    !currentPlayer?.active_dominance;

  return (
    <Box
      w={250}
      pos={isHand ? "absolute" : "relative"}
      bottom={isHand ? 0 : undefined}
      onMouseEnter={isHand ? () => setIsHovered(true) : undefined}
      onMouseLeave={isHand ? () => setIsHovered(false) : undefined}
      onClick={isHand ? () => submitPayloadOnClick() : undefined}
      style={{
        borderRadius: "8px 8px 0 0",
        overflow: "hidden",
        border: "1px solid #dee2e6",
        backgroundColor: "#fff",
        cursor: isHand ? "pointer" : "default",
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
                {cardData.cost?.map((s: any, i) => {
                  const sValue = s?.value || s;
                  const config = SUIT_CONFIG[sValue as SuitValue];
                  if (!config) {
                    console.warn("Missing SUIT_CONFIG for suit:", sValue, s);
                    return null;
                  }
                  const CostIcon = config.icon;
                  return (
                    <Box key={i} c={config.color}>
                      <CostIcon size={rem(40)} />
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
                ITEM: {cardData.item.label}
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
                color={map_suit_to_color(cardData.suit.value)}
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
