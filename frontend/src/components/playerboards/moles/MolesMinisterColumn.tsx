import {
  Group,
  Paper,
  ScrollArea,
  Stack,
  Text,
  Tooltip,
  rem,
} from "@mantine/core";
import { IconCheckbox, IconSquare } from "@tabler/icons-react";
import type { components } from "../../../api/types";

type Minister = components["schemas"]["MolesMinister"];

const MINISTER_TOOLTIPS: Record<string, string> = {
  Foremole:
    "Reveal any card to place a citadel or market in any clearing (matching or not) you rule.",
  Captain: "Initiate a battle.",
  Marshal: "Take a move.",
  Brigadier: "Take up to two moves or initiate up to two battles.",
  Banker:
    "Spend any number of cards (even one) of the same suit to score victory points in equal number.",
  Mayor: "Take the action of any swayed noble or squire.",
  "Duchess of Mud":
    "Score two victory points if all three tunnels are on the map.",
  "Baron of Dirt": "Score one victory point per market on the map.",
  "Earl of Stone": "Score one victory point per citadel on the map.",
};

interface MolesMinisterColumnProps {
  title: string;
  ministers: Minister[];
  showCheckbox: boolean;
}

export default function MolesMinisterColumn({
  title,
  ministers,
  showCheckbox,
}: MolesMinisterColumnProps) {
  return (
    <Paper
      withBorder
      radius="md"
      p="sm"
      style={{
        backgroundColor: "white",
        height: "100%",
        display: "flex",
        flexDirection: "column",
      }}
    >
      {/* Column Header */}
      <Text fw={700} tt="uppercase" size="sm" ta="center" mb="md">
        {title}
      </Text>

      {/* Ministers Scroll Area */}
      <ScrollArea h={250} offsetScrollbars>
        <Stack gap="xs">
          {ministers.length === 0 && (
            <Text c="dimmed" size="xs" ta="center" mt="xl">
              None
            </Text>
          )}
          {ministers.map((minister: Minister, i: number) => {
            const StatusIcon = minister.used ? IconCheckbox : IconSquare;
            const tooltip = MINISTER_TOOLTIPS[minister.name] || "";

            return (
              <Tooltip
                key={i}
                label={tooltip}
                multiline
                w={250}
                withArrow
                withinPortal
                openDelay={100}
                closeDelay={100}
                transitionProps={{ duration: 200, transition: "fade" }}
              >
                <Paper
                  withBorder
                  radius="sm"
                  p="xs"
                  style={{
                    overflow: "hidden",
                    borderColor: "#dee2e6",
                    backgroundColor: "#f9f9f9",
                  }}
                >
                  <Group justify="space-between" wrap="nowrap" gap="xs">
                    <Text
                      fw={600}
                      size="sm"
                      style={{
                        flex: 1,
                      }}
                    >
                      {minister.name}
                    </Text>
                    {showCheckbox && (
                      <StatusIcon
                        size={18}
                        style={{
                          opacity: 0.7,
                          minWidth: rem(18),
                          flexShrink: 0,
                        }}
                      />
                    )}
                  </Group>
                </Paper>
              </Tooltip>
            );
          })}
        </Stack>
      </ScrollArea>
    </Paper>
  );
}
