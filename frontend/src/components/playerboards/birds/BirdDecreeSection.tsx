import { Box, SimpleGrid, Text } from "@mantine/core";
import { IconHome2, IconPlus, IconShoe, IconSwords } from "@tabler/icons-react";
import BirdDecreeColumn from "./BirdDecreeColumn";

export const COLUMNS = [
  { label: "Recruit", code: "R", icon: IconPlus, color: "green" },
  { label: "Move", code: "M", icon: IconShoe, color: "blue" },
  { label: "Battle", code: "B", icon: IconSwords, color: "red" },
  { label: "Build", code: "U", icon: IconHome2, color: "yellow" },
];

export const columnHelperTextMapper: Record<string, string> = {
  Recruit: "Recruit one warrior at roost in matching clearing.",
  Move: "Move warriors from a matching clearing.",
  Battle: "Battle in a matching clearing",
  Build:
    "Build a roost in a matching clearing that you rule and don't have troops in.",
};

interface BirdDecreeSectionProps {
  decree: any[];
  viziers: any[];
}

export default function BirdDecreeSection({
  decree,
  viziers,
}: BirdDecreeSectionProps) {
  return (
    <Box>
      <Text size="lg" fw={800} mb="sm" ta="center">
        The Decree
      </Text>
      <SimpleGrid cols={4} spacing="md">
        {COLUMNS.map((col) => {
          const cardsInColumn = decree.filter(
            (d: any) => d.column === col.code,
          );
          const viziersInColumn = viziers.filter(
            (v: any) => v.column === col.code,
          );
          const columnItems = [...viziersInColumn, ...cardsInColumn];

          return (
            <BirdDecreeColumn
              key={col.code}
              col={col}
              columnHelperText={columnHelperTextMapper[col.label]}
              columnItems={columnItems}
            />
          );
        })}
      </SimpleGrid>
    </Box>
  );
}
