import { Group, Text, Tooltip, Stack, ThemeIcon } from "@mantine/core";
import {
  IconHome,
  IconAlertTriangle,
  IconUsers,
  IconArrowsSplit2,
} from "@tabler/icons-react";
import type { components } from "../../../api/types";
import CraftedItemsBox from "../../board/CraftedItemsBox";

interface MolesHeaderSectionProps {
  warriorsInSupply: number;
  tunnelsInSupply: number;
  craftedItems?: components["schemas"]["CraftedItemEntry"][];
}

export default function MolesHeaderSection({
  warriorsInSupply,
  tunnelsInSupply,
  craftedItems,
}: MolesHeaderSectionProps) {
  return (
    <Group justify="space-between" align="center" px="md" mb="xs">
      <Stack gap={0}>
        <Text
          size="1.5rem"
          fw={900}
          variant="gradient"
          gradient={{ from: "#8B6F47", to: "#d49d99", deg: 45 }}
          style={{ letterSpacing: "2px", fontFamily: "serif", lineHeight: 1 }}
        >
          Underground Duchy
        </Text>
        <Group gap="md" mt={4}>
          <Group gap={6}>
            <ThemeIcon color="#d49d99" variant="light" size="sm">
              <IconUsers size={14} />
            </ThemeIcon>
            <Text size="xs" fw={700} c="#8B6F47">
              {warriorsInSupply} WARRIORS IN BURROW
            </Text>
          </Group>
          <Group gap={6}>
            <ThemeIcon color="#d49d99" variant="light" size="sm">
              <IconArrowsSplit2 size={14} />
            </ThemeIcon>
            <Text size="xs" fw={700} c="#8B6F47">
              {tunnelsInSupply} TUNNELS IN SUPPLY
            </Text>
          </Group>
        </Group>
      </Stack>

      <Group gap="xl" align="center">
        <Tooltip
          label="The Burrow is adjacent to each clearing with a tunnel. You always rule the Burrow. Only you can enter the Burrow."
          multiline
          w={250}
          withArrow
          position="bottom"
        >
          <Group gap={4} style={{ cursor: "help" }}>
            <ThemeIcon color="#d49d99" variant="light" size="sm">
              <IconHome size={14} />
            </ThemeIcon>
            <Text size="xs" fw={700} c="#8B6F47" tt="uppercase">
              The Burrow
            </Text>
          </Group>
        </Tooltip>

        <Tooltip
          label="Whenever any number of your buildings are removed, return the swayed minister of highest rank to your Ministers stack, remove its crown from the game, and discard a random card."
          multiline
          w={250}
          withArrow
          position="bottom"
        >
          <Group gap={4} style={{ cursor: "help" }}>
            <ThemeIcon color="#d49d99" variant="light" size="sm">
              <IconAlertTriangle size={14} />
            </ThemeIcon>
            <Text size="xs" fw={700} c="#8B6F47" tt="uppercase">
              Price of Failure
            </Text>
          </Group>
        </Tooltip>

        <CraftedItemsBox craftedItems={craftedItems} />
      </Group>
    </Group>
  );
}
