import React from "react";
import { Button } from "@mantine/core";
import { useUndoAction } from "../../hooks/useUndoAction";
import { IconArrowBackUp } from "@tabler/icons-react";
import { useContext } from "react";
import { GameContext } from "../../contexts/GameProvider";

const UndoButton: React.FC = () => {
  const { gameId } = useContext(GameContext);
  const { undoMutation } = useUndoAction(gameId);

  return (
    <Button
      onClick={() => undoMutation.mutate()}
      loading={undoMutation.isPending}
      color="yellow"
      variant="filled"
      leftSection={<IconArrowBackUp size={20} />}
    >
      Undo
    </Button>
  );
};

export default UndoButton;
