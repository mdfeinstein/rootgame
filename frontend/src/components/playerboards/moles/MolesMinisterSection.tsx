import { SimpleGrid, Stack, Text, ScrollArea } from "@mantine/core";
import MolesMinisterColumn from "./MolesMinisterColumn";
import type { components } from "../../../api/types";

type Minister = components["schemas"]["MolesMinister"];

interface MolesMinisterSectionProps {
  ministers: Minister[];
}

export default function MolesMinisterSection({
  ministers,
}: MolesMinisterSectionProps) {
  const unswayedMinisters = ministers.filter((m) => !m.swayed);
  const swayedMinisters = ministers.filter((m) => m.swayed);

  return (
    <Stack gap="sm" style={{ flex: 1 }}>
      <Text size="md" fw={800} ta="center" tt="uppercase" c="dimmed">
        Ministers
      </Text>
      <ScrollArea h={280} offsetScrollbars style={{ flex: 1 }}>
        <SimpleGrid cols={2} spacing="sm">
          <MolesMinisterColumn
            title="Unswayed"
            ministers={unswayedMinisters}
            showCheckbox={false}
          />
          <MolesMinisterColumn
            title="Swayed"
            ministers={swayedMinisters}
            showCheckbox={true}
          />
        </SimpleGrid>
      </ScrollArea>
    </Stack>
  );
}
