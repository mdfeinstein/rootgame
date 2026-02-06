import { useContext } from "react";
import { Navigate, Outlet } from "react-router-dom";
import { UserContext } from "../contexts/UserProvider";
import { Center, Loader } from "@mantine/core";

const ProtectedRoute = () => {
  const { username, isLoading, isFetched } = useContext(UserContext);

  if (isLoading || !isFetched) {
    return (
      <Center style={{ width: "100vw", height: "100vh" }}>
        <Loader size="xl" />
      </Center>
    );
  }

  if (!username) {
    return <Navigate to="/login" replace />;
  }

  return <Outlet />;
};

export default ProtectedRoute;
