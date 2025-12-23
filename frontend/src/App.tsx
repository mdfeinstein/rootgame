import "./App.css";
import SvgBoard from "./components/board/Board";
import { GameActionProvider } from "./contexts/GameActionContext";
import Prompter from "./components/board/Prompter";
import Input from "./components/board/Input";
import DevSignIn from "./components/DevSignIn";
import Hand from "./components/cards/Hand";
import { GameProvider } from "./contexts/GameProvider";
import { UserProvider } from "./contexts/UserProvider";
import "@mantine/core/styles.css";
import { MantineProvider } from "@mantine/core";

function App() {
  return (
    <MantineProvider>
      <UserProvider>
        <GameProvider>
          <GameActionProvider>
            <div
              style={{
                display: "flex",
                flexDirection: "column",
              }}
            >
              <div
                style={{
                  display: "flex",
                  flexDirection: "row",
                  alignItems: "center",
                  justifyContent: "center",
                  width: "100%",
                  height: "100%",
                }}
              >
                <Prompter />
                <Input />
              </div>
              <DevSignIn />
            </div>
            <div
              style={{
                width: "800px",
                height: "800px",
              }}
            >
              <SvgBoard width={800} height={800} />
            </div>
            <Hand />
          </GameActionProvider>
        </GameProvider>
      </UserProvider>
    </MantineProvider>
  );
}

export default App;
