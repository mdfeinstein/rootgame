import {
  Group,
  Paper,
  Stack,
  Text,
  ThemeIcon,
  Tooltip,
  rem,
} from "@mantine/core";
import { IconCheckbox, IconSquare } from "@tabler/icons-react";
import { SUIT_CONFIG } from "../../../data/suitConfig";
import type { SuitValue } from "../../../data/suitConfig";

interface BirdDecreeColumnProps {
  col: {
    label: string;
    code: string;
    icon: any;
    color: string;
  };
  columnHelperText: string;
  columnItems: any[];
}

export default function BirdDecreeColumn({
  col,
  columnHelperText,
  columnItems,
}: BirdDecreeColumnProps) {
  const Icon = col.icon;

  return (
    <Paper
      withBorder
      radius="md"
      p="sm"
      style={{
        backgroundColor: "white",
        minHeight: "300px",
        display: "flex",
        flexDirection: "column",
      }}
    >
      {/* Column Header */}
      <Tooltip
        label={columnHelperText}
        multiline
        w={200}
        withArrow
        transitionProps={{ duration: 200, transition: "fade" }}
      >
        <Group mb="md" justify="center" gap="xs">
          <ThemeIcon color={col.color} variant="light">
            <Icon size={18} />
          </ThemeIcon>
          <Text fw={700} tt="uppercase" size="sm">
            {col.label}
          </Text>
        </Group>
      </Tooltip>

      {/* Cards Stack */}
      <Stack gap="xs" style={{ flexGrow: 1 }}>
        {columnItems.length === 0 && (
          <Text c="dimmed" size="xs" ta="center" mt="xl">
            Empty
          </Text>
        )}
        {columnItems.map((item: any, i: number) => {
          const isVizier = !item.card;
          const cardData = isVizier
            ? { title: "Vizier", suit: "b" }
            : item.card;

          const suitConfig =
            SUIT_CONFIG[cardData.suit as SuitValue] || SUIT_CONFIG["b"];
          const SuitIcon = suitConfig.icon;
          const StatusIcon = item.fulfilled ? IconCheckbox : IconSquare;

          return (
            <Paper
              key={i}
              withBorder
              radius="sm"
              style={{
                overflow: "hidden",
                // Mimic card styling
                borderColor: "#dee2e6",
                backgroundColor: "#fff",
              }}
            >
              <Group
                bg={suitConfig.color}
                px="xs"
                py={rem(4)}
                gap="xs"
                wrap="nowrap"
                style={{ color: "white" }}
              >
                <SuitIcon size={20} />
                <Text
                  fw={700}
                  size="xs"
                  style={{
                    letterSpacing: rem(0.5),
                    textTransform: "uppercase",
                  }}
                >
                  {cardData.title}
                </Text>
                <StatusIcon
                  size={18}
                  style={{
                    marginLeft: "auto",
                    opacity: 0.9,
                    minWidth: rem(18), // Ensure it takes up space
                    flexShrink: 0, // Prevent squashing
                  }}
                />
              </Group>
            </Paper>
          );
        })}
      </Stack>
    </Paper>
  );
}
