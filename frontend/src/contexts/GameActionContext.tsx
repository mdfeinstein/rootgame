import { createContext, useState } from "react";
import type { GameActionStep, StepPayload } from "../hooks/useGameActionQuery";
import useGameActionQuery from "../hooks/useGameActionQuery";

// components when clicked may pass any or all of this information.
// the callback will use the relevant data to submit to the server
export type SubmitPayload = {
  clearing_number?: number;
  building_type?: string;
  piece_type?: string;
  leader?: string;
};

const GameActionContext = createContext<any>({});

const GameActionProvider = ({
  gameId,
  children,
}: {
  gameId: number;
  children: React.ReactNode;
}) => {
  const {
    baseEndpoint,
    actionInfo,
    error,
    isLoading,
    isError,
    isSuccess,
    submitPayloadMutation,
  } = useGameActionQuery(gameId);

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
      }}
    >
      {children}
    </GameActionContext.Provider>
  );
};

export { GameActionContext, GameActionProvider };
