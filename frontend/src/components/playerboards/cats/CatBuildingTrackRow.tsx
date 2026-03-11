import { Grid, Paper, Text, ThemeIcon, Tooltip } from "@mantine/core";

interface CatBuildingTrackRowProps {
  label: string;
  vps: number[];
  countOnBoard: number;
  icon: any;
  color: string;
}

export default function CatBuildingTrackRow({
  label,
  vps,
  countOnBoard,
  icon: Icon,
  color,
}: CatBuildingTrackRowProps) {
  return (
    <Grid gutter="xs" align="center" mb="sm">
      <Grid.Col span={2}>
        <Text fw={700} size="sm" ta="right" c="dimmed">
          {label}
        </Text>
      </Grid.Col>
      <Grid.Col span={10}>
        <Grid columns={6} gutter="xs">
          {vps.map((vp, index) => {
            // Logic: index 0 is valid if countOnBoard > 5?
            // If countOnBoard is 6, indices 0-5 are filled.
            // If countOnBoard is 5, indices 1-5 are filled, 0 is empty.
            // Filled condition: index >= (6 - countOnBoard)
            const isFilled = index >= 6 - countOnBoard;

            return (
              <Grid.Col span={1} key={index}>
                <Paper
                  radius="md"
                  h={50}
                  withBorder
                  style={{
                    backgroundColor: isFilled
                      ? "var(--mantine-color-gray-0)"
                      : "var(--mantine-color-gray-1)",
                    borderColor: isFilled
                      ? "transparent"
                      : "var(--mantine-color-gray-3)",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    position: "relative",
                    overflow: "hidden",
                    boxShadow: isFilled
                      ? "var(--mantine-shadow-sm)"
                      : "inset 0 2px 4px rgba(0,0,0,0.1)",
                  }}
                >
                  {/* VP Number (always rendered, covered by building if filled) */}
                  {!isFilled && (
                    <Text fw={800} size="lg" c="gray.5">
                      +{vp} VP
                    </Text>
                  )}

                  {/* Building Piece */}
                  {isFilled && (
                    <Tooltip label={`+${vp} VP`} withArrow>
                      <ThemeIcon
                        size={40}
                        radius="md"
                        variant="gradient"
                        gradient={{
                          from: `${color}.5`,
                          to: `${color}.7`,
                          deg: 45,
                        }}
                      >
                        <Icon size="60%" color="white" />
                      </ThemeIcon>
                    </Tooltip>
                  )}
                </Paper>
              </Grid.Col>
            );
          })}
        </Grid>
      </Grid.Col>
    </Grid>
  );
}
