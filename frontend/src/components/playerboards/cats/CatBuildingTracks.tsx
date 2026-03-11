import { Box, Center, Grid, Paper, Text } from "@mantine/core";
import {
  IconCampfireFilled,
  IconHammer,
  IconTent,
  IconWood,
} from "@tabler/icons-react";
import CatBuildingTrackRow from "./CatBuildingTrackRow";

const WOOD_COSTS = [0, 1, 2, 3, 3, 4];
const SAWMILL_VPS = [0, 1, 2, 3, 4, 5];
const WORKSHOP_VPS = [0, 2, 2, 3, 4, 5];
const RECRUITER_VPS = [0, 1, 2, 3, 3, 4];

const TRACK_CONFIG = [
  {
    label: "Recruiters",
    prop: "recruiters",
    vps: RECRUITER_VPS,
    icon: IconTent,
    color: "orange",
  },
  {
    label: "Workshops",
    prop: "workshops",
    vps: WORKSHOP_VPS,
    icon: IconHammer,
    color: "orange",
  },
  {
    label: "Sawmills",
    prop: "sawmills",
    vps: SAWMILL_VPS,
    icon: IconCampfireFilled,
    color: "orange",
  },
];

interface CatBuildingTracksProps {
  counts: {
    sawmills: number;
    workshops: number;
    recruiters: number;
  };
}

export default function CatBuildingTracks({ counts }: CatBuildingTracksProps) {
  return (
    <Box>
      {/* Column Headers (Wood Costs) */}
      <Grid gutter="xs" align="center" mb="xs">
        <Grid.Col span={2}>{/* Empty for Row Label */}</Grid.Col>
        <Grid.Col span={10}>
          <Grid columns={6} gutter="xs">
            {WOOD_COSTS.map((cost, i) => (
              <Grid.Col span={1} key={i}>
                <Center>
                  <Paper
                    radius="xl"
                    bg="orange.2"
                    w={30}
                    h={30}
                    style={{
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                    }}
                  >
                    <IconWood />
                    <Text size="sm" fw={700} c="orange.9">
                      {cost}
                    </Text>
                  </Paper>
                </Center>
              </Grid.Col>
            ))}
          </Grid>
        </Grid.Col>
      </Grid>

      {/* Rows */}
      {TRACK_CONFIG.map((track) => (
        <CatBuildingTrackRow
          key={track.label}
          label={track.label}
          vps={track.vps}
          icon={track.icon}
          color={track.color}
          countOnBoard={counts[track.prop as keyof typeof counts]}
        />
      ))}
    </Box>
  );
}
