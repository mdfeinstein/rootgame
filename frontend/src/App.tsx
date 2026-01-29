import "./App.css";
import SvgBoard from "./components/board/Board";
import { GameActionProvider } from "./contexts/GameActionContext";
import Prompter from "./components/board/Prompter";
import CraftedCardPrompter from "./components/board/CraftedCardPrompter";
import Input from "./components/board/Input";
import DevSignIn from "./components/DevSignIn";
import Hand from "./components/cards/Hand";
import { GameProvider } from "./contexts/GameProvider";
import { UserProvider } from "./contexts/UserProvider";
import "@mantine/core/styles.css";
import { Group, MantineProvider, Stack } from "@mantine/core";
import PlayerColumn from "./components/player/PlayerColumn";
import { PlayerProvider } from "./contexts/PlayerProvider";
import UndoButton from "./components/prompts/UndoButton";

function App() {
  return (
    <MantineProvider>
      <UserProvider>
        <GameProvider>
          <PlayerProvider>
            <GameActionProvider>
              <Group>
                <Stack>
                  <PlayerColumn />
                  <UndoButton />
                </Stack>
                <div
                  style={{
                    width: "800px",
                    height: "800px",
                  }}
                >
                  <SvgBoard width={800} height={800} />
                </div>
              </Group>
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
                  <Stack>
                    <CraftedCardPrompter />
                    <Prompter />
                  </Stack>
                  {/* <Input /> */}
                </div>
                <DevSignIn />
              </div>
              <Hand />
            </GameActionProvider>
          </PlayerProvider>
        </GameProvider>
      </UserProvider>
    </MantineProvider>
  );
}

export default App;
