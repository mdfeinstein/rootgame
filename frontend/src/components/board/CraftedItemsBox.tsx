import { Paper, Text, Tooltip } from "@mantine/core";
import type { components } from "../../api/types";
import { getItemIcon } from "../../utils/itemIcons";

interface CraftedItemsBoxProps {
  craftedItems?: components["schemas"]["CraftedItemEntry"][];
}

const CraftedItemsBox: React.FC<CraftedItemsBoxProps> = ({ craftedItems }) => {
  const ITEM_WIDTH = 36;
  const GAP = 4;
  const PADDING = 8;
  const ITEM_WITH_GAP = ITEM_WIDTH + GAP;

  const boxWidth = PADDING * 2 + 4.5 * ITEM_WITH_GAP;

  return (
    <div style={{ position: "relative", paddingTop: "6px" }}>
      <div
        style={{
          width: `${boxWidth}px`,
          border: "1px solid var(--mantine-color-gray-3)",
          borderRadius: "4px",
          padding: `${PADDING}px`,
          minHeight: "36px",
          backgroundColor: "white",
          position: "relative",
        }}
      >
        <Text
          size="10px"
          fw={700}
          c="dimmed"
          style={{
            position: "absolute",
            top: "-8px",
            left: "8px",
            backgroundColor: "#fef6e4",
            paddingRight: "3px",
            paddingLeft: "3px",
          }}
        >
          CRAFTED ITEMS
        </Text>

        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: `${GAP}px`,
            flexWrap: "wrap",
            overflowY: "auto",
            width: "100%",
            maxHeight: "52px",
          }}
        >
          {craftedItems && craftedItems.length > 0 ? (
            craftedItems.map((item, idx) => (
              <Tooltip
                key={idx}
                label={`${item.item.label}${item.exhausted ? " (exhausted)" : ""}`}
                withArrow
                position="top"
              >
                <Paper
                  p="4"
                  withBorder
                  radius="sm"
                  style={{
                    backgroundColor: item.exhausted ? "#f0f0f0" : "white",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    opacity: item.exhausted ? 0.5 : 1,
                    width: `${ITEM_WIDTH}px`,
                    height: `${ITEM_WIDTH}px`,
                    flexShrink: 0,
                  }}
                >
                  {getItemIcon(item.item.label, 20)}
                </Paper>
              </Tooltip>
            ))
          ) : (
            <Text size="xs" c="dimmed" fw={500}>
              No items
            </Text>
          )}
        </div>
      </div>
    </div>
  );
};

export default CraftedItemsBox;
