import "./App.css";
import SvgBoard from "./components/board/Board";
import { GameActionProvider } from "./contexts/GameActionContext";
import Prompter from "./components/board/Prompter";
import Input from "./components/board/Input";
import DevSignIn from "./components/DevSignIn";

function App() {
  return (
    <GameActionProvider gameId={1}>
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
      <SvgBoard width={800} height={800} />
    </GameActionProvider>
  );
}

export default App;
