import { useContext, useState } from "react";
import { UserContext } from "../../contexts/UserProvider";
import useGetPlayerHandQuery from "../../hooks/useGetPlayerHandQuery";
import { GameCard } from "./Card";
import { GameContext } from "../../contexts/GameProvider";
import { Box, Group } from "@mantine/core";

const Hand = () => {
  const { username } = useContext(UserContext);
  const { gameId } = useContext(GameContext);
  const { playerHand } = useGetPlayerHandQuery(gameId, username);
  const [isHovered, setIsHovered] = useState(false);
  return (
    <Group
      mt={"50px"}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
      wrap="nowrap"
      pos="relative"
      gap={"xs"}
      justify="center"
      align="center"
      style={{
        width: "100%", // Use 100% to give them room to spread
        height: "60px", // Fixed height for the "tray"
        // overflow: "visible" is default, but ensures cards can float out
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
