import useGetPlayerHandQuery from "../../hooks/useGetPlayerHandQuery";
import Card from "./Card";

const Hand = () => {
  const { playerHand } = useGetPlayerHandQuery();
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
