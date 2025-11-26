import { useContext, useState } from "react";
import { GameActionContext } from "../../contexts/GameActionContext";
import type { SubmitPayload } from "../../contexts/GameActionContext";

export default function Input() {
  const { submitPayloadCallback } = useContext(GameActionContext);
  const [input_type, setInputType] = useState<string>("");
  const [input_value, setInputValue] = useState<string>("");

  const submitPayloadOnClick = () => {
    const payload: Record<string, string> = {};
    payload[input_type] = input_value;
    submitPayloadCallback(payload);
    // setInputType("");
    setInputValue("");
  };
  const submitPayloadOnConfirm = () => {
    const payload: Record<string, boolean> = {};
    payload["confirm"] = true;
    submitPayloadCallback(payload);
  };
  const submitPayloadOnCancel = () => {
    const payload: Record<string, boolean> = {};
    payload["confirm"] = false;
    submitPayloadCallback(payload);
  };
  return (
    <>
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
        <input
          type="text"
          value={input_type}
          placeholder="input_type"
          onChange={(e) => setInputType(e.target.value)}
        />
        <input
          type="text"
          value={input_value}
          placeholder="input_value"
          onChange={(e) => setInputValue(e.target.value)}
        />
        <button onClick={submitPayloadOnClick}>Submit</button>
      </div>
      <div>
        <button onClick={submitPayloadOnConfirm}> Confirm </button>
        <button onClick={submitPayloadOnCancel}> Cancel </button>
      </div>
    </>
  );
}
