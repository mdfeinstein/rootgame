import { Stack, Text, Tooltip, Box, Title, ScrollArea } from "@mantine/core";

export default function CatTurnFlow() {
  return (
    <ScrollArea h={350} offsetScrollbars p="xs">
      <Stack gap="sm">
        {/* Birdsong */}
        <Box>
          <Box bg="orange.6" p="xs" mb="xs" style={{ borderRadius: '4px' }}>
            <Title order={4} c="white" tt="uppercase">Birdsong</Title>
          </Box>
          <Tooltip label="Place one wood token at each sawmill." withArrow>
            <Text size="sm" fw={600} style={{ cursor: 'help' }}>Place one wood</Text>
          </Tooltip>
        </Box>

        {/* Daylight */}
        <Box>
          <Box bg="blue.4" p="xs" mb="xs" style={{ borderRadius: '4px' }}>
            <Title order={4} c="white" tt="uppercase">Daylight</Title>
          </Box>
          <Stack gap={4}>
            <Tooltip label="Craft cards using workshops matching the clearing's suit." withArrow>
              <Text size="sm" fw={600} style={{ cursor: 'help' }}>1st: Craft</Text>
            </Tooltip>
            
            <Tooltip label="Take up to 3 actions, plus one per Bird card spent." withArrow>
              <Text size="sm" fw={600} style={{ cursor: 'help' }}>2nd: Take up to 3 actions</Text>
            </Tooltip>

            <Stack gap={2} pl="sm">
              <Tooltip label="Initiate a battle in a clearing where you have warriors." withArrow>
                <Text size="xs" fw={500} style={{ cursor: 'help' }}>• Battle</Text>
              </Tooltip>
              
              <Tooltip label="Take up to two moves." withArrow>
                <Text size="xs" fw={500} style={{ cursor: 'help' }}>• March</Text>
              </Tooltip>
              
              <Tooltip label="Once per turn, place one warrior at each recruiter." withArrow>
                <Text size="xs" fw={500} style={{ cursor: 'help' }}>• Recruit</Text>
              </Tooltip>
              
              <Tooltip label="In a clearing you rule, place a building, spending its cost in wood connected through any number of clearings you rule." withArrow multiline w={250}>
                <Text size="xs" fw={500} style={{ cursor: 'help' }}>• Build</Text>
              </Tooltip>
              
              <Tooltip label="Spend a card to place one wood at a sawmill in a matching clearing." withArrow>
                <Text size="xs" fw={500} style={{ cursor: 'help' }}>• Overwork</Text>
              </Tooltip>
            </Stack>
          </Stack>
        </Box>

        {/* Evening */}
        <Box>
          <Box bg="indigo.4" p="xs" mb="xs" style={{ borderRadius: '4px' }}>
            <Title order={4} c="white" tt="uppercase">Evening</Title>
          </Box>
          <Tooltip label="Draw 1 card, plus 1 card per card-draw symbol showing on recruiters. Discard down to 5 cards." withArrow multiline w={250}>
            <Text size="sm" fw={600} style={{ cursor: 'help' }}>Draw and Discard</Text>
          </Tooltip>
        </Box>
      </Stack>
    </ScrollArea>
  );
}
