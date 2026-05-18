import { useContext } from "react";
import { GameActionContext } from "../../contexts/GameActionProvider";
import useGameActionQuery from "../../hooks/useGameActionQuery";
import { GameContext } from "../../contexts/GameProvider";
import type { Option } from "../../hooks/useGameActionQuery";
import { Button, Group, Tooltip } from "@mantine/core";
import { factionToMantineColor } from "../../utils/factionColors";

const OptionPrompt = () => {
  const { gameId } = useContext(GameContext);
  const { submitPayloadCallback } = useContext(GameActionContext);
  const { actionInfo } = useGameActionQuery(gameId);
  const faction = actionInfo?.faction?.label?.replace(" ", "");
  console.log(faction);
  const options = actionInfo?.options;
  if (!options) return null;
  const optionType = actionInfo?.payload_details?.[0]?.type;
  const onSelect = (option: Option) => {
    const payload: Record<string, string> = {};
    if (!optionType) return;
    payload[optionType] = option.value;
    submitPayloadCallback(payload);
  };
  return (
    <Group>
      {options?.map((option, i) => (
        <Tooltip
          key={i}
          label={option.info}
          disabled={!option.info}
          position="top"
          withArrow
          multiline
          w={220}
          openDelay={500}
        >
          <Button
            onClick={() => onSelect(option)}
            bg={factionToMantineColor(faction as any)}
            styles={{
              root: {
                "&:hover": {
                  border: "2px solid gold",
                  backgroundColor: "black",
                },
              },
            }}
          >
            {option.label}
          </Button>
        </Tooltip>
      ))}
    </Group>
  );
};

export default OptionPrompt;
