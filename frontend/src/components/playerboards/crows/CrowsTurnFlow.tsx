import { Box, ScrollArea, Stack, Text, Tooltip, Paper, Divider } from "@mantine/core";

export default function CrowsTurnFlow() {
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
            <Tooltip label="Craft using plots, face up or down.">
              <Text size="sm" fw={700} style={{ cursor: "help" }}>1st: Craft</Text>
            </Tooltip>
            <Tooltip label="Flip plot tokens face up in clearings with Corvid warriors. For each flip, score +1 VP per face-up plot on the map, then resolve its flip effect." multiline w={250}>
              <Text size="sm" fw={700} style={{ cursor: "help" }}>2nd: Flip</Text>
            </Tooltip>
            <Tooltip label="Once per turn, spend any card to place one warrior in each matching clearing." multiline w={250}>
              <Text size="sm" fw={700} style={{ cursor: "help" }}>3rd: Recruit</Text>
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
            Take up to 3 actions:
          </Text>
          <Stack gap={4} mt={4}>
            <Tooltip label="Remove one Corvid warrior, plus one per plot token you placed this turn, from a clearing with no plot token to place a facedown plot token there." multiline w={250}>
              <Text size="sm" fw={700} style={{ cursor: "help" }}>Plot</Text>
            </Tooltip>
            <Tooltip label="Move warriors regardless of rule.">
              <Text size="sm" fw={700} style={{ cursor: "help" }}>Move</Text>
            </Tooltip>
            <Tooltip label="Swap two plot tokens, both face up or down, on the map.">
              <Text size="sm" fw={700} style={{ cursor: "help" }}>Trick</Text>
            </Tooltip>
            <Tooltip label="Initiate a battle.">
              <Text size="sm" fw={700} style={{ cursor: "help" }}>Battle</Text>
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
            <Tooltip label="You may take an extra Daylight action. If you do, you do not draw cards during the next step." multiline w={250}>
              <Text size="sm" fw={700} style={{ cursor: "help" }}>1st: Exert</Text>
            </Tooltip>
            <Tooltip label="Draw 1 card, plus 1 card per Extortion token showing on the map. Discard down to 5 cards." multiline w={250}>
              <Text size="sm" fw={700} style={{ cursor: "help" }}>2nd: Draw & Discard</Text>
            </Tooltip>
          </Stack>
        </Box>
      </Stack>
    </ScrollArea>
  );
}
