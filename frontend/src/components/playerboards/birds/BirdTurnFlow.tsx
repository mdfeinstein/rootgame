import { Stack, Text, Tooltip, Box, Title, ScrollArea } from "@mantine/core";

export default function BirdTurnFlow() {
  return (
    <ScrollArea h={350} offsetScrollbars p="xs">
      <Stack gap="sm">
        {/* Birdsong */}
        <Box>
          <Box bg="orange.6" p="xs" mb="xs" style={{ borderRadius: "4px" }}>
            <Title order={4} c="white" tt="uppercase">
              Birdsong
            </Title>
          </Box>
          <Stack gap={4}>
            <Tooltip label="If your hand is empty, draw 1 card." withArrow>
              <Text size="sm" fw={600} style={{ cursor: "help" }}>
                1st: Draw if empty
              </Text>
            </Tooltip>
            <Tooltip
              label="Add 1 or 2 cards to the Decree. Only one card added may be a Bird."
              withArrow
            >
              <Text size="sm" fw={600} style={{ cursor: "help" }}>
                2nd: Add to Decree
              </Text>
            </Tooltip>
            <Tooltip
              label="If you have no roosts, place a roost and 3 warriors in the clearing with the fewest total warriors."
              withArrow
              multiline
              w={250}
            >
              <Text size="sm" fw={600} style={{ cursor: "help" }}>
                3rd: A New Dynasty
              </Text>
            </Tooltip>
          </Stack>
        </Box>

        {/* Daylight */}
        <Box>
          <Box bg="blue.4" p="xs" mb="xs" style={{ borderRadius: "4px" }}>
            <Title order={4} c="white" tt="uppercase">
              Daylight
            </Title>
          </Box>
          <Stack gap={4}>
            <Tooltip
              label="Craft cards using roosts matching the clearing's suit."
              withArrow
            >
              <Text size="sm" fw={600} style={{ cursor: "help" }}>
                1st: Craft
              </Text>
            </Tooltip>
            <Tooltip
              label="Resolve the Decree from left to right, taking one action per card in a matching clearing."
              withArrow
              multiline
              w={250}
            >
              <Text size="sm" fw={600} style={{ cursor: "help" }}>
                2nd: Resolve Decree
              </Text>
            </Tooltip>
          </Stack>
        </Box>

        {/* Evening */}
        <Box>
          <Box bg="indigo.4" p="xs" mb="xs" style={{ borderRadius: "4px" }}>
            <Title order={4} c="white" tt="uppercase">
              Evening
            </Title>
          </Box>
          <Stack gap={4}>
            <Tooltip
              label="Score victory points of the rightmost empty space on the Roosts track."
              withArrow
              multiline
              w={250}
            >
              <Text size="sm" fw={600} style={{ cursor: "help" }}>
                Score VP
              </Text>
            </Tooltip>
            <Tooltip
              label="Draw 1 card, plus 1 card per card-draw symbol showing on the Roosts track. Discard down to 5 cards."
              withArrow
              multiline
              w={250}
            >
              <Text size="sm" fw={600} style={{ cursor: "help" }}>
                Draw and Discard
              </Text>
            </Tooltip>
          </Stack>
        </Box>

        {/* Turmoil */}
        <Box
          mt="md"
          p="xs"
          bg="gray.1"
          style={{
            borderRadius: "4px",
            border: "1px solid var(--mantine-color-gray-3)",
          }}
        >
          <Box bg="gray.8" p="xs" mb="xs" style={{ borderRadius: "4px" }}>
            <Title order={4} c="white" tt="uppercase" ta="center">
              Turmoil
            </Title>
          </Box>
          <Text size="xs" fw={700} c="dimmed" mb={4} fs="italic">
            If you cannot take an action in the Decree...
          </Text>
          <Stack gap={2}>
            <Tooltip
              label="Lose 1 VP per Bird card (including Viziers) on the Decree."
              withArrow
            >
              <Text size="xs" fw={600} style={{ cursor: "help" }}>
                1. Humiliate
              </Text>
            </Tooltip>
            <Tooltip label="Discard the Decree, except Viziers." withArrow>
              <Text size="xs" fw={600} style={{ cursor: "help" }}>
                2. Purge
              </Text>
            </Tooltip>
            <Tooltip
              label="Flip leader face down and choose a new one. Reassign Viziers."
              withArrow
            >
              <Text size="xs" fw={600} style={{ cursor: "help" }}>
                3. Depose
              </Text>
            </Tooltip>
            <Tooltip
              label="Immediately end Daylight and go to Evening."
              withArrow
            >
              <Text size="xs" fw={600} style={{ cursor: "help" }}>
                4. Rest
              </Text>
            </Tooltip>
          </Stack>
        </Box>
      </Stack>
    </ScrollArea>
  );
}
