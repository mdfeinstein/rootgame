import { useContext } from "react";
import { GameActionContext } from "../../contexts/GameActionContext";
import useGameActionQuery from "../../hooks/useGameActionQuery";
import { GameContext } from "../../contexts/GameProvider";
import type { Option } from "../../hooks/useGameActionQuery";
import { Button, Group } from "@mantine/core";
import useGetPlayerQuery from "../../hooks/useGetPlayerQuery";
import { UserContext } from "../../contexts/UserProvider";

const factionColorMap = {
  Cats: "orange",
  Birds: "blue",
  WoodlandAlliance: "green",
};

const OptionPrompt = () => {
  const { gameId } = useContext(GameContext);
  const { submitPayloadCallback } = useContext(GameActionContext);
  const { actionInfo } = useGameActionQuery(gameId);
  const faction = actionInfo?.faction.replace(" ", "");
  console.log(faction);
  console.log(factionColorMap[faction as keyof typeof factionColorMap]);
  const options = actionInfo?.options;
  if (!options) return null;
  const optionType = actionInfo?.payload_details[0].type;
  const onSelect = (option: Option) => {
    const payload: Record<string, string> = {};
    if (!optionType) return;
    payload[optionType] = option.value;
    submitPayloadCallback(payload);
  };
  return (
    <Group>
      {options?.map((option, i) => (
        <Button
          key={i}
          onClick={() => onSelect(option)}
          bg={factionColorMap[faction as keyof typeof factionColorMap]}
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
      ))}
    </Group>
  );
};

export default OptionPrompt;
