import { useContext } from "react";
import { UserContext } from "../contexts/UserProvider";
import { Button, Group, Text } from "@mantine/core";
import { useNavigate } from "react-router-dom";

export default function DemoUserSwitch() {
  const { signInMutation } = useContext(UserContext);
  const navigate = useNavigate();

  const handleDemoLogin = (username: string) => {
    signInMutation.mutate(
      { username, password: "password" },
      {
        onSuccess: () => {
          // If we are on login page, this will move us to lobby
          // If we are on lobby page, it will just refresh the user context
          // navigate("/lobby"); // Optional if we want to force nav, but context update might be enough
          navigate("/lobby"); // ensuring we go to lobby
        },
      },
    );
  };

  return (
    <Group justify="center" mt="md">
      <Text size="sm" c="dimmed">
        Demo Users:
      </Text>
      <Button
        variant="outline"
        size="xs"
        onClick={() => handleDemoLogin("user1")}
      >
        User 1
      </Button>
      <Button
        variant="outline"
        size="xs"
        onClick={() => handleDemoLogin("user2")}
      >
        User 2
      </Button>
      <Button
        variant="outline"
        size="xs"
        onClick={() => handleDemoLogin("user3")}
      >
        User 3
      </Button>
    </Group>
  );
}
