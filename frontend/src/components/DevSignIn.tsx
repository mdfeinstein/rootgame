import { useContext, useEffect, useState } from "react";
import { UserContext } from "../contexts/UserProvider";
import { GameContext } from "../contexts/GameProvider";

export default function DevSignIn() {
  const { signInMutation: signIn, username } = useContext(UserContext);
  const { session } = useContext(GameContext);

  // status of which faction we currently think we are representing
  const [activeButton, setActiveButton] = useState<string | null>(null);

  useEffect(() => {
    if (session?.players && username) {
      const currentPlayer = session.players.find(
        (p: any) => p.username.toLowerCase() === username.toLowerCase(),
      );
      if (currentPlayer?.faction?.value) {
        const factionMap: Record<string, string> = {
          ca: "Cats",
          bi: "Birds",
          wa: "Woodland Alliance",
          cr: "Crows",
        };
        setActiveButton(factionMap[currentPlayer.faction.value] || null);
      } else {
        setActiveButton(null);
      }
    }
  }, [session, username]);

  const signInByFaction = (factionCode: string, label: string) => {
    const players = session?.players || [];
    const player = players.find((p: any) => p.faction?.value === factionCode);

    if (player) {
      signIn.mutate({ username: player.username, password: "password" });
      setActiveButton(label);
    } else {
      console.log(`No player has picked ${label} yet.`);
    }
  };

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "row",
        alignItems: "center",
        justifyContent: "center",
      }}
    >
      <button
        onClick={() => signInByFaction("ca", "Cats")}
        style={{
          background: activeButton === "Cats" ? "orange" : "white",
        }}
      >
        Cats
      </button>
      <button
        onClick={() => signInByFaction("bi", "Birds")}
        style={{
          background: activeButton === "Birds" ? "blue" : "white",
        }}
      >
        Birds
      </button>
      <button
        onClick={() => signInByFaction("wa", "Woodland Alliance")}
        style={{
          background: activeButton === "Woodland Alliance" ? "green" : "white",
        }}
      >
        WA
      </button>
      <button
        onClick={() => signInByFaction("cr", "Crows")}
        style={{
          background: activeButton === "Crows" ? "indigo" : "white",
          color: activeButton === "Crows" ? "white" : "black",
        }}
      >
        Crows
      </button>
    </div>
  );
}
