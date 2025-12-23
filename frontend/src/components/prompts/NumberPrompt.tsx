import { useContext, useState } from "react";
import { GameContext } from "../../contexts/GameProvider";
import { GameActionContext } from "../../contexts/GameActionContext";
import useGameActionQuery from "../../hooks/useGameActionQuery";

const NumberPrompt = () => {
  const { gameId } = useContext(GameContext);
  const { submitPayloadCallback } = useContext(GameActionContext);
  const { actionInfo } = useGameActionQuery(gameId);
  const [number, setNumber] = useState(0);
  if (
    !actionInfo?.payload_details ||
    actionInfo?.payload_details.length === 0 ||
    actionInfo?.payload_details[0].type !== "number"
  )
    return null;
  const onSubmit = () => {
    submitPayloadCallback({ number: number });
    setNumber(1);
  };

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "row",
        alignItems: "center",
        justifyContent: "center",
      }}
    >
      <input
        type="number"
        value={number}
        min={1}
        onChange={(e) => setNumber(parseInt(e.target.value))}
      />
      <button onClick={onSubmit}>Submit</button>
    </div>
  );
};

export default NumberPrompt;
