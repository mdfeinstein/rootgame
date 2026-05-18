import { Stack, Text, Tooltip, Box, Title, ScrollArea } from "@mantine/core";

export default function MolesTurnFlow() {
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
          <Tooltip
            label="Place one warrior in the Burrow, plus one per warrior showing on Citadel track."
            withArrow
          >
            <Text size="sm" fw={600} style={{ cursor: "help" }}>
              Place warriors
            </Text>
          </Tooltip>
        </Box>

        {/* Daylight */}
        <Box>
          <Box bg="blue.4" p="xs" mb="xs" style={{ borderRadius: "4px" }}>
            <Title order={4} c="white" tt="uppercase">
              Daylight
            </Title>
          </Box>
          <Stack gap={4}>
            <Tooltip label="Take up to 2 actions in any order." withArrow>
              <Text size="sm" fw={600} style={{ cursor: "help" }}>
                1st: Take up to 2 actions
              </Text>
            </Tooltip>

            <Stack gap={2} pl="sm">
              <Tooltip
                label="Move warriors from the Burrow or a matching clearing into a matching clearing."
                withArrow
                multiline
                w={250}
              >
                <Text size="xs" fw={500} style={{ cursor: "help" }}>
                  • Move
                </Text>
              </Tooltip>

              <Tooltip label="Initiate a battle in a clearing." withArrow>
                <Text size="xs" fw={500} style={{ cursor: "help" }}>
                  • Battle
                </Text>
              </Tooltip>

              <Tooltip
                label="Place one warrior from the Burrow into a matching clearing."
                withArrow
              >
                <Text size="xs" fw={500} style={{ cursor: "help" }}>
                  • Recruit
                </Text>
              </Tooltip>

              <Tooltip
                label="Reveal a card to place a citadel or market in a matching clearing you rule."
                withArrow
                multiline
                w={250}
              >
                <Text size="xs" fw={500} style={{ cursor: "help" }}>
                  • Build
                </Text>
              </Tooltip>

              <Tooltip
                label="Spend a card to place up to 4 warriors from the Burrow into a matching clearing with no tunnel, then move up to 4 from that clearing."
                withArrow
                multiline
                w={250}
              >
                <Text size="xs" fw={500} style={{ cursor: "help" }}>
                  • Dig
                </Text>
              </Tooltip>
            </Stack>

            <Tooltip
              label="You may take the action of each swayed minister once in any order."
              withArrow
              multiline
              w={250}
            >
              <Text size="sm" fw={600} style={{ cursor: "help" }}>
                2nd: Take swayed minister actions
              </Text>
            </Tooltip>

            <Tooltip
              label="Reveal any number of cards matching clearings with any Duchy pieces to sway a minister."
              withArrow
              multiline
              w={250}
            >
              <Text size="sm" fw={600} style={{ cursor: "help" }}>
                3rd: Sway a minister
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
              label="Revealed Bird cards are discarded, and the rest are returned to hand."
              withArrow
              multiline
              w={250}
            >
              <Text size="sm" fw={600} style={{ cursor: "help" }}>
                1st: Return and discard revealed
              </Text>
            </Tooltip>

            <Tooltip
              label="Craft using citadels and markets."
              withArrow
            >
              <Text size="sm" fw={600} style={{ cursor: "help" }}>
                2nd: Craft
              </Text>
            </Tooltip>

            <Tooltip
              label="Draw 1 card, plus 1 card per market showing. Return all unrevealed cards to hand. Discard down to 5 cards."
              withArrow
              multiline
              w={250}
            >
              <Text size="sm" fw={600} style={{ cursor: "help" }}>
                3rd: Draw and discard
              </Text>
            </Tooltip>
          </Stack>
        </Box>
      </Stack>
    </ScrollArea>
  );
}
