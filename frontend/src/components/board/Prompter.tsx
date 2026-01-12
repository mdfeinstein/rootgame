import { GameActionContext } from "../../contexts/GameActionContext";
import { useContext } from "react";
import OptionPrompt from "../prompts/OptionPrompt";
import NumberPrompt from "../prompts/NumberPrompt";

export default function Prompter() {
  const { faction, actionPrompt, error, cancelProcess } =
    useContext(GameActionContext);
  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        width: "100%",
        height: "100%",
      }}
    >
      <div>{faction}</div>
      <div>{actionPrompt}</div>
      <div style={{ color: "red" }}>{error}</div>
      <OptionPrompt />
      <NumberPrompt />
      <button onClick={() => cancelProcess()}>Cancel</button>
    </div>
  );
}
