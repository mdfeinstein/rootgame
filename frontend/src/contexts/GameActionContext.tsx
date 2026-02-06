import { createContext, useContext, useState } from "react";
import type { GameActionStep, StepPayload } from "../hooks/useGameActionQuery";
import useGameActionQuery from "../hooks/useGameActionQuery";
import { GameContext } from "./GameProvider";

// components when clicked may pass any or all of this information.
// the callback will use the relevant data to submit to the server
export type SubmitPayload = {
  clearing_number?: number;
  building_type?: string;
  piece_type?: string;
  leader?: string;
};

const GameActionContext = createContext<any>({});

const GameActionProvider = ({ children }: { children: React.ReactNode }) => {
  const { gameId, isGameStarted } = useContext(GameContext);
  const {
    baseEndpoint,
    actionInfo,
    error,
    isLoading,
    isError,
    isSuccess,
    submitPayloadMutation,
    cancelProcess,
    startActionOverride,
  } = useGameActionQuery(gameId, isGameStarted);

  const callBack = (submitPayload: SubmitPayload) => {
    // find relevant types from click
    const payload: Record<string, unknown> = {};
    if (!actionInfo?.payload_details) return;
    for (const payload_detail of actionInfo?.payload_details) {
      if (payload_detail.type in submitPayload) {
        if (
          submitPayload[payload_detail.type as keyof SubmitPayload] !==
          undefined
        )
          payload[payload_detail.name] =
            submitPayload[payload_detail.type as keyof SubmitPayload];
      } else {
        console.log("missing detail", payload_detail);
        console.log("submitPayload", submitPayload);
        // submitPayload missing required detail, skip
        return;
      }
    }
    // submit to server
    submitPayloadMutation.mutate(payload);
  };

  return (
    <GameActionContext.Provider
      value={{
        faction: actionInfo?.faction,
        actionPrompt: actionInfo?.prompt,
        error,
        submitPayloadCallback: callBack,
        cancelProcess,
        startActionOverride,
      }}
    >
      {children}
    </GameActionContext.Provider>
  );
};

export { GameActionContext, GameActionProvider };
