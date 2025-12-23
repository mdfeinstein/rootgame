import { useContext } from "react";
import type { CardType } from "../../hooks/useGetPlayerHandQuery";
import { GameActionContext } from "../../contexts/GameActionContext";
const Card = ({ cardData }: { cardData: CardType }) => {
  const { submitPayloadCallback } = useContext(GameActionContext);
  const submitPayloadOnClick = () => {
    submitPayloadCallback({ card: cardData.card_name });
  };
  const colormap = {
    r: "red",
    y: "yellow",
    o: "orange",
    b: "blue",
  };
  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        width: "100%",
        height: "100%",
        background: "#00000095",
      }}
      onClick={() => submitPayloadOnClick()}
    >
      <div style={{ color: colormap[cardData.suit] }}>{cardData.suit}</div>
      <div>{cardData.title}</div>
      <div>{cardData.text}</div>
      <div>{cardData.cost}</div>
      {/* <div>{cardData.craftable}</div>
      <div>{cardData.item}</div>
      <div>{cardData.craftedPoints}</div>
      <div>{cardData.ambush}</div>
      <div>{cardData.dominance}</div> */}
    </div>
  );
};

export default Card;
