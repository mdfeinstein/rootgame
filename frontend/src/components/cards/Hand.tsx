import { useContext } from "react";
import { UserContext } from "../../contexts/UserProvider";
import useGetPlayerHandQuery from "../../hooks/useGetPlayerHandQuery";
import Card from "./Card";
import { GameContext } from "../../contexts/GameProvider";

const Hand = () => {
  const { username } = useContext(UserContext);
  const { gameId } = useContext(GameContext);
  const { playerHand } = useGetPlayerHandQuery(gameId, username);
  return (
    <div
      style={{
        display: "flex",
        flexDirection: "row",
        alignItems: "center",
        justifyContent: "center",
        width: "50%",
        height: "100%",
      }}
    >
      {playerHand?.map((card, i) => (
        <div
          key={i}
          style={{
            margin: "10px",
          }}
        >
          <Card cardData={card} />
        </div>
      ))}
    </div>
  );
};

export default Hand;
