import { useContext, useState } from "react";
import { UserContext } from "../../contexts/UserProvider";
import useGetPlayerHandQuery from "../../hooks/useGetPlayerHandQuery";
import { GameCard } from "./Card";
import { GameContext } from "../../contexts/GameProvider";
import { Box, Group } from "@mantine/core";

const Hand = () => {
  const { username } = useContext(UserContext);
  const { gameId, isGameStarted } = useContext(GameContext);
  const { playerHand } = useGetPlayerHandQuery(gameId, username, isGameStarted);
  const [isHovered, setIsHovered] = useState(false);
  return (
    <Group
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
      wrap="nowrap"
      justify="center"
      align="center"
      style={{
        position: "fixed",
        bottom: 0,
        left: 0,
        width: "100vw",
        zIndex: 1000,
        backgroundColor: "rgba(255, 255, 255, 0.9)", // slightly more opaque
        paddingBottom: "10px",
        borderTop: "1px solid #eee",
        boxShadow: "0 -4px 12px rgba(0,0,0,0.1)", // slightly stronger shadow
        margin: 0,
      }}
    >
      {playerHand?.map((card, i) => (
        <Box
          key={i}
          w={150}
          pos="relative"
          style={
            {
              // margin: "10px",
            }
          }
        >
          <GameCard cardData={card} isCollapsed={!isHovered} index={i} />
        </Box>
      ))}
    </Group>
  );
};

export default Hand;
