import { Paper, Stack, Text, Grid, Tooltip, Group } from "@mantine/core";
import type { components } from "../../../api/types";

type Citadel = components["schemas"]["MolesCitadel"];
type Market = components["schemas"]["MolesMarket"];

const BUILDING_SYMBOLS: Record<string, string> = {
  citadel: "⬢", // Hexagon for citadels
  market: "◆", // Diamond for markets
};

const BUILDING_TOOLTIPS: Record<string, string> = {
  citadel: "Citadel - Provides extra warriors in supply",
  market: "Market - Provides card draw",
};

interface MolesBuildingTrackProps {
  citadels: Citadel[];
  markets: Market[];
}

export default function MolesBuildingTrack({
  citadels,
  markets,
}: MolesBuildingTrackProps) {
  const citadelsNotOnMap = citadels.filter(
    (c) => !c.building.clearing_number
  );
  const marketsNotOnMap = markets.filter(
    (m) => !m.building.clearing_number
  );

  return (
    <Paper withBorder p="sm" radius="md" bg="white" shadow="sm">
      <Stack gap="sm">
        <Text fw={700} size="sm" tt="uppercase">
          Buildings in Supply
        </Text>

        <Grid gutter="sm">
          {/* Citadels */}
          <Grid.Col span={{ base: 6 }}>
            <Stack gap="xs">
              <Tooltip label={BUILDING_TOOLTIPS.citadel} withArrow>
                <Text fw={600} size="sm">
                  Citadels ({citadelsNotOnMap.length})
                </Text>
              </Tooltip>
              <Group gap="xs" wrap="wrap">
                {citadelsNotOnMap.length === 0 ? (
                  <Text c="dimmed" size="xs">
                    All on map
                  </Text>
                ) : (
                  citadelsNotOnMap.map((_, i) => (
                    <Tooltip
                      key={i}
                      label="Citadel in supply"
                      withArrow
                    >
                      <Paper
                        p="xs"
                        bg="#e8dcc4"
                        radius="sm"
                        style={{
                          border: "2px solid #8B6F47",
                          minWidth: 32,
                          display: "flex",
                          alignItems: "center",
                          justifyContent: "center",
                        }}
                      >
                        <Text fw={700} size="lg">
                          {BUILDING_SYMBOLS.citadel}
                        </Text>
                      </Paper>
                    </Tooltip>
                  ))
                )}
              </Group>
            </Stack>
          </Grid.Col>

          {/* Markets */}
          <Grid.Col span={{ base: 6 }}>
            <Stack gap="xs">
              <Tooltip label={BUILDING_TOOLTIPS.market} withArrow>
                <Text fw={600} size="sm">
                  Markets ({marketsNotOnMap.length})
                </Text>
              </Tooltip>
              <Group gap="xs" wrap="wrap">
                {marketsNotOnMap.length === 0 ? (
                  <Text c="dimmed" size="xs">
                    All on map
                  </Text>
                ) : (
                  marketsNotOnMap.map((_, i) => (
                    <Tooltip
                      key={i}
                      label="Market in supply"
                      withArrow
                    >
                      <Paper
                        p="xs"
                        bg="#e8dcc4"
                        radius="sm"
                        style={{
                          border: "2px solid #8B6F47",
                          minWidth: 32,
                          display: "flex",
                          alignItems: "center",
                          justifyContent: "center",
                        }}
                      >
                        <Text fw={700} size="lg">
                          {BUILDING_SYMBOLS.market}
                        </Text>
                      </Paper>
                    </Tooltip>
                  ))
                )}
              </Group>
            </Stack>
          </Grid.Col>
        </Grid>
      </Stack>
    </Paper>
  );
}
