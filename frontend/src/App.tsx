import "./App.css";
import "@mantine/core/styles.css";
import { MantineProvider } from "@mantine/core";
import {
  createBrowserRouter,
  RouterProvider,
  Navigate,
} from "react-router-dom";
import { GameProvider } from "./contexts/GameProvider";
import { UserProvider } from "./contexts/UserProvider";
import LoginPage from "./pages/Login";
import LobbyPage from "./pages/Lobby";
import GamePage from "./pages/GamePage";
import ProtectedRoute from "./components/ProtectedRoute";

const router = createBrowserRouter([
  {
    path: "/login",
    element: <LoginPage />,
  },
  {
    element: <ProtectedRoute />,
    children: [
      {
        path: "/lobby",
        element: <LobbyPage />,
      },
      {
        path: "/game/:gameId",
        element: <GamePage />,
      },
      {
        path: "/",
        element: <Navigate to="/lobby" replace />,
      },
    ],
  },
]);

function App() {
  return (
    <MantineProvider>
      <UserProvider>
        <GameProvider>
          <RouterProvider router={router} />
        </GameProvider>
      </UserProvider>
    </MantineProvider>
  );
}

export default App;
