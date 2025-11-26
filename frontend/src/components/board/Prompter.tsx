import { GameActionContext } from "../../contexts/GameActionContext";
import { useContext } from "react";

export default function Prompter() {
  const { faction, actionPrompt, error } = useContext(GameActionContext);
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
    </div>
  );
}
