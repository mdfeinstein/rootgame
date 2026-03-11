import { Box, Paper, Stack, Text } from "@mantine/core";

export default function CrowsAbilities() {
  return (
    <Box>
      <Text fw={700} size="sm" mb="xs" c="indigo.8">
        Faction Abilities
      </Text>
      <Stack gap="xs">
        <Paper p="xs" radius="sm" bg="indigo.1">
          <Text size="sm" fw={600}>
            Nimble
          </Text>
          <Text size="xs">
            You can move regardless of who rules the origin or destination
            clearing.
          </Text>
        </Paper>
        <Paper p="xs" radius="sm" bg="indigo.1">
          <Text size="sm" fw={600}>
            Exposure
          </Text>
          <Text size="xs">
            Other players can guess your facedown plots to remove them.
          </Text>
        </Paper>
      </Stack>
    </Box>
  );
}
