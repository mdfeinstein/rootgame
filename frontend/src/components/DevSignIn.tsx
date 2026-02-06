import { useMutation } from "@tanstack/react-query";
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
      if (currentPlayer?.faction) {
        const factionMap: Record<string, string> = {
          ca: "Cats",
          bi: "Birds",
          wa: "WA",
        };
        setActiveButton(factionMap[currentPlayer.faction] || null);
      } else {
        setActiveButton(null);
      }
    }
  }, [session, username]);

  const signInByFaction = (factionCode: string, label: string) => {
    const players = session?.players || [];
    const player = players.find((p: any) => p.faction === factionCode);

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
        onClick={() => signInByFaction("wa", "WA")}
        style={{
          background: activeButton === "WA" ? "green" : "white",
        }}
      >
        WA
      </button>
    </div>
  );
}
