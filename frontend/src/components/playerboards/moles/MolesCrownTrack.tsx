import { Paper, Group, SimpleGrid, Text, Tooltip } from "@mantine/core";
import { IconCrown } from "@tabler/icons-react";
import type { components } from "../../../api/types";

type MolesCrown = components["schemas"]["MolesCrown"];

const TIERS = [
  { type: "squire", label: "Squires", vp: 1 },
  { type: "noble", label: "Nobles", vp: 2 },
  { type: "lord", label: "Lords", vp: 3 },
];

interface MolesCrownTrackProps {
  crowns: MolesCrown[];
}

export default function MolesCrownTrack({ crowns }: MolesCrownTrackProps) {
  const availableCrowns = crowns.filter((c) => !c.used);

  return (
    <div style={{ position: "relative", paddingTop: "6px" }}>
      <div
        style={{
          border: "1px solid var(--mantine-color-gray-3)",
          borderRadius: "8px",
          padding: "12px",
          backgroundColor: "white",
          boxShadow: "0 1px 3px rgba(0, 0, 0, 0.05)",
          position: "relative",
        }}
      >
        <Text
          size="xs"
          fw={700}
          c="dimmed"
          tt="uppercase"
          style={{
            position: "absolute",
            top: "-8px",
            left: "50%",
            transform: "translateX(-50%)",
            backgroundColor: "#f5ead6",
            paddingRight: "6px",
            paddingLeft: "6px",
          }}
        >
          Crowns
        </Text>

        <Group gap="md" justify="center">
          {TIERS.map((tier) => {
            const tierCrowns = availableCrowns.filter((c) => c.type === tier.type);

            return (
              <div key={tier.type}>
                <Text size="xs" fw={600} c="dimmed" ta="center" mb="xs">
                  {tier.label} (+{tier.vp})
                </Text>
                <SimpleGrid cols={3} spacing="xs">
                  {[0, 1, 2].map((index) => {
                    const crown = tierCrowns[index];
                    const isFilled = !!crown;

                    return (
                      <Tooltip
                        key={index}
                        label={`+${tier.vp} VP scored when swaying`}
                        withArrow
                        withinPortal
                      >
                        <Paper
                          w={32}
                          h={32}
                          withBorder
                          radius="sm"
                          style={{
                            backgroundColor: isFilled
                              ? "#e8dcc4"
                              : "var(--mantine-color-gray-1)",
                            display: "flex",
                            alignItems: "center",
                            justifyContent: "center",
                            borderColor: isFilled
                              ? "#d49d99"
                              : "var(--mantine-color-gray-3)",
                            borderStyle: isFilled ? "solid" : "dashed",
                            cursor: "help",
                          }}
                        >
                          {isFilled ? (
                            <IconCrown
                              size={16}
                              color="#8B6F47"
                            />
                          ) : (
                            <Text size="xs" fw={700} c="dimmed">
                              +{tier.vp}
                            </Text>
                          )}
                        </Paper>
                      </Tooltip>
                    );
                  })}
                </SimpleGrid>
              </div>
            );
          })}
        </Group>
      </div>
    </div>
  );
}
