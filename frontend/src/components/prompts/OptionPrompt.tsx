import { useContext } from "react";
import { GameActionContext } from "../../contexts/GameActionContext";
import useGameActionQuery from "../../hooks/useGameActionQuery";
import { GameContext } from "../../contexts/GameProvider";
import type { Option } from "../../hooks/useGameActionQuery";
const OptionPrompt = () => {
  const { gameId } = useContext(GameContext);
  const { submitPayloadCallback } = useContext(GameActionContext);
  const { actionInfo } = useGameActionQuery(gameId);
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
    <div
      style={{
        display: "flex",
        flexDirection: "row",
        alignItems: "center",
        justifyContent: "center",
        width: "100%",
        height: "100%",
      }}
    >
      {options?.map((option, i) => (
        <button
          key={i}
          onClick={() => onSelect(option)}
          style={
            {
              // background: option === options[0] ? "orange" : "white",
            }
          }
        >
          {option.label}
        </button>
      ))}
    </div>
  );
};

export default OptionPrompt;
