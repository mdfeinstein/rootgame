import { Badge, Indicator, Tooltip } from "@mantine/core";
import { IconCards } from "@tabler/icons-react";
import { useState } from "react";
import useCraftedCardsQuery from "../../hooks/useCraftedCardsQuery";
import CraftedCardModal from "./CraftedCardModal";

interface CraftedCardBadgeProps {
  gameId: number;
  faction: string;
  factionLabel: string;
}

const CraftedCardBadge = ({
  gameId,
  faction,
  factionLabel,
}: CraftedCardBadgeProps) => {
  const { craftedCards } = useCraftedCardsQuery(gameId, faction);
  const [modalOpen, setModalOpen] = useState(false);

  const count = craftedCards?.length || 0;
  const isDisabled = count === 0;

  return (
    <div
      onClick={(e) => {
        if (!isDisabled) {
          e.stopPropagation();
        }
      }}
      onMouseDown={(e) => {
        if (!isDisabled) e.stopPropagation();
      }}
      style={{ display: "inline-block" }}
    >
      <div
        onClick={(e) => {
          if (!isDisabled) {
            setModalOpen(true);
          }
        }}
        style={{ display: "inline-block" }}
      >
        <Tooltip label={isDisabled ? "No crafted cards" : "View crafted cards"}>
          <Indicator
            label={count}
            size={16}
            offset={2}
            disabled={isDisabled}
            color="blue"
          >
            <Badge
              variant="light"
              color={isDisabled ? "gray" : "blue"}
              leftSection={<IconCards size={14} />}
              style={{ cursor: isDisabled ? "default" : "pointer" }}
            >
              Crafted
            </Badge>
          </Indicator>
        </Tooltip>
      </div>

      <CraftedCardModal
        isOpen={modalOpen}
        onClose={() => setModalOpen(false)}
        craftedCards={craftedCards}
        factionLabel={factionLabel}
      />
    </div>
  );
};

export default CraftedCardBadge;
