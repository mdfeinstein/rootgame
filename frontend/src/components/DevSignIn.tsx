import { useMutation } from "@tanstack/react-query";
import { useEffect, useState } from "react";
const djangoUrl = import.meta.env.VITE_DJANGO_URL;

export default function DevSignIn() {
  const signIn = useMutation({
    mutationFn: async (loginData: { username: string; password: string }) => {
      const response = await fetch(`${djangoUrl}/api/token/`, {
        method: "POST",
        // credentials: "include",
        body: JSON.stringify({
          username: loginData.username,
          password: loginData.password,
        }),
        headers: {
          "Content-Type": "application/json",
        },
      });
      return response.json();
    },
    onSuccess: async (data) => {
      localStorage.setItem("accessToken", data.access);
      localStorage.setItem("refreshToken", data.refresh);
      console.log("success", data);
    },
    onError: (error) => {
      console.log("error", error);
    },
  });
  // by default, sign in cats
  const [signedIn, setSignedIn] = useState<string | null>(null);
  const signInCallback = (faction: string) => {
    switch (faction) {
      case "Cats":
        signIn.mutate({ username: "user1", password: "password" });
        setSignedIn("Cats");
        break;
      case "Birds":
        signIn.mutate({ username: "user2", password: "password" });
        setSignedIn("Birds");
        break;
      case "WA":
        signIn.mutate({ username: "user3", password: "password" });
        setSignedIn("WA");
        break;
      default:
        break;
    }
  };
  useEffect(() => {
    signInCallback("Cats");
  }, []);

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
        onClick={() => signInCallback("Cats")}
        style={{
          background: signedIn === "Cats" ? "orange" : "white",
        }}
      >
        Cats
      </button>
      <button
        onClick={() => signInCallback("Birds")}
        style={{
          background: signedIn === "Birds" ? "blue" : "white",
        }}
      >
        Birds
      </button>
      <button
        onClick={() => signInCallback("WA")}
        style={{
          background: signedIn === "WA" ? "green" : "white",
        }}
      >
        WA
      </button>
    </div>
  );
}
