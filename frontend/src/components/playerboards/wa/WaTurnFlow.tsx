import { Box, ScrollArea, Stack, Text, Tooltip, Paper, Divider } from "@mantine/core";

export default function WaTurnFlow() {
  return (
    <ScrollArea h={350} offsetScrollbars>
      <Stack gap="sm" p="xs">
        {/* Birdsong */}
        <Box>
          <Paper bg="orange.5" px="xs" py={2} radius="sm">
            <Text size="xs" fw={900} c="white" tt="uppercase">
              Birdsong
            </Text>
          </Paper>
          <Stack gap={4} mt={4}>
            <Tooltip label="Spend 2 supporters matching a sympathetic clearing. Remove all enemy pieces there. Place matching base and warriors there equal to total number of matching sympathetic clearings. Place a warrior in the Officers box." multiline w={250}>
              <Text size="sm" fw={700} style={{ cursor: "help" }}>
                1st: Revolt <Text span fz="xs" fw={400}>(any number of times)</Text>
              </Text>
            </Tooltip>
            <Tooltip label="Spend number of supporters listed on Sympathy track to place a sympathy, adjacent to sympathetic clearing if possible. Supporters must match the target clearing." multiline w={250}>
              <Text size="sm" fw={700} style={{ cursor: "help" }}>
                2nd: Spread Sympathy <Text span fz="xs" fw={400}>(any number of times)</Text>
              </Text>
            </Tooltip>
          </Stack>
        </Box>

        <Divider />

        {/* Daylight */}
        <Box>
          <Paper bg="blue.5" px="xs" py={2} radius="sm">
            <Text size="xs" fw={900} c="white" tt="uppercase">
              Daylight
            </Text>
          </Paper>
          <Text size="xs" c="dimmed" fs="italic" mt={2}>
            You may take these actions any number of times:
          </Text>
          <Stack gap={4} mt={4}>
            <Tooltip label="Craft using sympathy tokens.">
              <Text size="sm" fw={700} style={{ cursor: "help" }}>Craft</Text>
            </Tooltip>
            <Tooltip label="Add a card from hand to your Supporters stack.">
              <Text size="sm" fw={700} style={{ cursor: "help" }}>Mobilize</Text>
            </Tooltip>
            <Tooltip label="Spend a card from hand matching a built base to place a warrior in the Officers box.">
              <Text size="sm" fw={700} style={{ cursor: "help" }}>Train</Text>
            </Tooltip>
          </Stack>
        </Box>

        <Divider />

        {/* Evening */}
        <Box>
          <Paper bg="indigo.5" px="xs" py={2} radius="sm">
            <Text size="xs" fw={900} c="white" tt="uppercase">
              Evening
            </Text>
          </Paper>
          <Stack gap={4} mt={4}>
            <Tooltip label="Perform Move, Battle, Recruit, or Organize up to the number of officers you have." multiline w={250}>
              <Text size="sm" fw={700} style={{ cursor: "help" }}>
                1st: Military Operations <Text span fz="xs" fw={400}>(up to officers)</Text>
              </Text>
            </Tooltip>
            <Tooltip label="Draw 1 card, plus 1 card per bonus draw symbol showing on bases. Discard down to 5 cards." multiline w={250}>
              <Text size="sm" fw={700} style={{ cursor: "help" }}>
                2nd: Draw & Discard
              </Text>
            </Tooltip>
          </Stack>
        </Box>
      </Stack>
    </ScrollArea>
  );
}
