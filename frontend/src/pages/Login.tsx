import { useContext, useState } from "react";
import { UserContext } from "../contexts/UserProvider";
import {
  TextInput,
  PasswordInput,
  Button,
  Paper,
  Title,
  Container,
  Stack,
  Alert,
} from "@mantine/core";
import { useNavigate } from "react-router-dom";
import { IconAlertCircle } from "@tabler/icons-react";

const LoginPage = () => {
  const { signInMutation } = useContext(UserContext);
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const navigate = useNavigate();

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    signInMutation.mutate(
      { username, password },
      {
        onSuccess: () => {
          navigate("/lobby");
        },
      },
    );
  };

  return (
    <Container size={420} my={40}>
      <Title ta="center" order={1}>
        Welcome Back!
      </Title>

      <Paper withBorder shadow="md" p={30} mt={30} radius="md">
        <form onSubmit={handleLogin}>
          <Stack>
            <TextInput
              label="Username"
              placeholder="Your username"
              required
              value={username}
              onChange={(e) => setUsername(e.currentTarget.value)}
            />
            <PasswordInput
              label="Password"
              placeholder="Your password"
              required
              value={password}
              onChange={(e) => setPassword(e.currentTarget.value)}
            />
            {signInMutation.isError && (
              <Alert
                icon={<IconAlertCircle size="1rem" />}
                title="Error"
                color="red"
              >
                {signInMutation.error instanceof Error
                  ? signInMutation.error.message
                  : "Invalid credentials. Please try again."}
              </Alert>
            )}
            <Button
              type="submit"
              fullWidth
              mt="xl"
              loading={signInMutation.isPending}
            >
              Sign in
            </Button>
          </Stack>
        </form>
      </Paper>
    </Container>
  );
};

export default LoginPage;
