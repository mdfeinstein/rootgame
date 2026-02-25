import {
  Button,
  Paper,
  Title,
  Text,
  Group,
  Stack,
  ThemeIcon,
} from "@mantine/core";
import { IconBolt } from "@tabler/icons-react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";

const djangoUrl = import.meta.env.VITE_DJANGO_URL;

const fetchWithAuth = async (url: string, options: RequestInit = {}) => {
  const token = localStorage.getItem("accessToken");
  const headers = {
    ...options.headers,
    "Content-Type": "application/json",
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  };
  const response = await fetch(url, { ...options, headers });
  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }
  return response;
};

export const useCreateDemoGame = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async () => {
      const resp = await fetchWithAuth(`${djangoUrl}/api/game/create-demo/`, {
        method: "POST",
      });
      return resp.json();
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["activeGames"] });
      queryClient.invalidateQueries({ queryKey: ["joinableGames"] });
    },
  });
};

const DemoQuickStart = () => {
  const navigate = useNavigate();
  const createDemoGameMutation = useCreateDemoGame();

  const handleDemoQuickStart = () => {
    createDemoGameMutation.mutate(undefined, {
      onSuccess: (data) => {
        if (data && data.game_id) {
          navigate(`/game/${data.game_id}`);
        }
      },
    });
  };

  return (
    <Paper
      withBorder
      p="md"
      radius="md"
      shadow="sm"
      style={{
        borderColor: "var(--mantine-color-teal-outline)",
        backgroundColor: "var(--mantine-color-teal-light)",
      }}
    >
      <Group justify="space-between" align="center">
        <Stack gap="xs">
          <Group gap="sm">
            <ThemeIcon color="teal" variant="light" size="lg">
              <IconBolt size={20} />
            </ThemeIcon>
            <Title order={3} c="teal.9">
              Demo Game Quick Start
            </Title>
          </Group>
          <Text size="sm" c="dimmed">
            Instantly create and start a 3-player demo game (Cats, Birds, WA)
            with users `user1`, `user2`, and `user3`.
          </Text>
        </Stack>
        <Button
          color="teal"
          size="md"
          leftSection={<IconBolt size={18} />}
          onClick={handleDemoQuickStart}
          loading={createDemoGameMutation.isPending}
        >
          Create Demo Game
        </Button>
      </Group>
    </Paper>
  );
};

export default DemoQuickStart;
