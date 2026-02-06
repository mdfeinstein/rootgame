import { useContext } from "react";
import { GameContext } from "../../contexts/GameProvider";
import useGetPlayersInfoQuery from "../../hooks/useGetPlayersInfoQuery";
import { Stack, Title, Loader, Center } from "@mantine/core";
import PlayerIcon from "./PlayerIcon";
const PlayerColumn = () => {
  const { gameId, isGameStarted } = useContext(GameContext);
  const { players } = useGetPlayersInfoQuery(gameId, isGameStarted);
  const sortedPlayers = [...(players || [])].sort(
    (a, b) => a.turn_order - b.turn_order,
  );

  console.log(sortedPlayers);
  return (
    <Stack gap="xs" w={300}>
      <Title order={5} c="dimmed" style={{ textTransform: "uppercase" }}>
        Turn Order
      </Title>

      {sortedPlayers.map((player) => (
        <PlayerIcon player={player} />
      ))}
    </Stack>
  );
};

export default PlayerColumn;
