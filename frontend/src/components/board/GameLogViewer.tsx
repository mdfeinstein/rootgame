import {
  Drawer,
  ScrollArea,
  Text,
  Stack,
  Paper,
  Group,
  ThemeIcon,
  Collapse,
  ActionIcon,
  Tooltip,
} from "@mantine/core";
import {
  IconHistory,
  IconChevronRight,
  IconChevronDown,
} from "@tabler/icons-react";
import { useState, useContext, useRef, useEffect } from "react";
import { UserContext } from "../../contexts/UserProvider";
import useGameLogQuery from "../../hooks/useGameLogQuery";
import type { GameLogType } from "../../hooks/useGameLogQuery";
import { FACTION_CONFIG } from "../../data/factionConfig";

interface GameLogViewerProps {
  gameId: number;
  isOpen: boolean;
  onToggle: () => void;
}

const getFactionInfo = (prefix: string | null) => {
  switch (prefix) {
    case "ca":
      return { label: "Cats", color: FACTION_CONFIG.cats.color };
    case "bi":
      return { label: "Birds", color: FACTION_CONFIG.birds.color };
    case "wa":
      return { label: "Woodland Alliance", color: FACTION_CONFIG["woodland-alliance"].color };
    case "cr":
      return { label: "Crows", color: FACTION_CONFIG.crows.color };
    default:
      return { label: prefix, color: "gray" };
  }
};

const getPhaseColor = (phase: string | undefined) => {
  if (!phase) return "blue";
  switch (phase.toLowerCase()) {
    case "birdsong": return "orange.6";
    case "daylight": return "blue.4";
    case "evening": return "indigo.4";
    default: return "blue";
  }
};

const LogNode = ({ log, depth = 0, defaultOpened = true }: { log: GameLogType; depth?: number; defaultOpened?: boolean }) => {
  const [opened, setOpened] = useState(defaultOpened);

  const details = log.details as any;
  const children = (log.children as unknown as GameLogType[]) || [];
  const hasChildren = children.length > 0;

  // Update opened state if defaultOpened changes (e.g. when logs refresh)
  useEffect(() => {
    setOpened(defaultOpened);
  }, [defaultOpened]);

  // Simple rendering logic relying on backend generated text
  const renderDetails = () => {
    if (log.log_type === "TURN") {
      return <Text fw={700}>Turn {details.turn_number}</Text>;
    }
    if (log.log_type === "PHASE") {
      return (
        <Text fw={700} c={getPhaseColor(details.phase)} tt="uppercase" size="xs">
          {details.text}
        </Text>
      );
    }

    if (details?.text) {
      return <Text size="sm">{details.text}</Text>;
    }

    return <Text size="sm">{log.log_type}</Text>;
  };

  return (
    <Stack gap={0}>
      <Group
        gap={4}
        wrap="nowrap"
        align="center"
        onClick={() => hasChildren && setOpened(!opened)}
        style={{
          cursor: hasChildren ? "pointer" : "default",
          padding: "4px 0",
          "&:hover": { backgroundColor: "rgba(0,0,0,0.02)" },
        }}
      >
        <div style={{ width: depth * 16, height: 1, flexShrink: 0 }} />
        {hasChildren ? (
          <ThemeIcon
            variant="subtle"
            size="sm"
            color="gray"
            style={{ flexShrink: 0 }}
          >
            {opened ? (
              <IconChevronDown size={14} />
            ) : (
              <IconChevronRight size={14} />
            )}
          </ThemeIcon>
        ) : (
          <div style={{ width: 22, flexShrink: 0 }} />
        )}

        {log.player_faction && (
          <Text size="xs" fw={700} c={getFactionInfo(log.player_faction).color} style={{ flexShrink: 0 }}>
            [{getFactionInfo(log.player_faction).label?.toUpperCase()}]
          </Text>
        )}

        {renderDetails()}
      </Group>

      {hasChildren && (
        <Collapse in={opened}>
          <Stack gap={2} mt={2}>
            {children.map((child: GameLogType, idx: number) => (
              <LogNode key={child.id || idx} log={child} depth={depth + 1} />
            ))}
          </Stack>
        </Collapse>
      )}
    </Stack>
  );
};

const GameLogViewer: React.FC<GameLogViewerProps> = ({
  gameId,
  isOpen,
  onToggle,
}) => {
  const { username } = useContext(UserContext);
  const { gameLogs, isLoading } = useGameLogQuery(gameId, username || "");

  const viewport = useRef<HTMLDivElement>(null);
  const scrollTargetRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (isOpen) {
      // Repeat scroll a few times to handle animations and rendering delays
      let count = 0;
      const interval = setInterval(() => {
        scrollTargetRef.current?.scrollIntoView({ behavior: 'instant', block: 'end' });
        count++;
        if (count >= 5) clearInterval(interval);
      }, 200);
      return () => clearInterval(interval);
    }
  }, [isOpen]);

  // Handle new logs while already open
  useEffect(() => {
    if (isOpen && gameLogs) {
      scrollTargetRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' });
    }
  }, [gameLogs]);

  return (
    <>
      <Tooltip label="Game Action Log" withArrow position="bottom" zIndex={2000}>
        <ActionIcon
          variant="light"
          onClick={onToggle}
          w={64}
          h={48}
          color="violet"
          radius="md"
        >
          <IconHistory size={28} />
        </ActionIcon>
      </Tooltip>

      <Drawer
        opened={isOpen}
        onClose={onToggle}
        position="right"
        size="sm"
        title={
          <Text size="lg" fw={700}>
            Game Action Log
          </Text>
        }
        styles={{
          root: {
            zIndex: 900,
            pointerEvents: "none",
          },
          inner: {
            top: "80px",
            height: "calc(100vh - 80px)",
          },
          content: {
            pointerEvents: "all",
            height: "100%",
            boxShadow: "-4px 0 12px rgba(0,0,0,0.1)",
            borderTop: "1px solid #ddd",
          },
          header: {
            backgroundColor: "#fef6e4",
            borderBottom: "2px solid #ddd",
          },
          body: {
            backgroundColor: "#fef6e4",
            padding: "16px",
            height: "calc(100vh - 140px)", // Account for header and offset
          },
          overlay: {
            top: "80px",
            height: "calc(100vh - 80px)",
          }
        }}
        withOverlay={false}
        trapFocus={false}
        closeOnClickOutside={false}
        padding="md"
        lockScroll={false}
      >
        <ScrollArea h="100%" offsetScrollbars viewportRef={viewport}>
          <Stack gap="sm">
            {isLoading && <Text c="dimmed">Loading logs...</Text>}
            {!isLoading && (!gameLogs || gameLogs.length === 0) && (
              <Text c="dimmed" ta="center" mt="md">
                The game log is currently empty.
              </Text>
            )}

            {!isLoading && gameLogs && (
              <Stack gap={1}>
                {gameLogs.map((log: GameLogType, idx: number) => (
                  <Paper
                    key={log.id || idx}
                    withBorder
                    p={2}
                    shadow="xs"
                    radius={0}
                    style={{ backgroundColor: "#fafafa", borderLeft: 'none', borderRight: 'none' }}
                  >
                    <LogNode 
                      log={log} 
                      defaultOpened={idx === gameLogs.length - 1} 
                    />
                  </Paper>
                ))}
                <div ref={scrollTargetRef} style={{ height: 1 }} />
              </Stack>
            )}
          </Stack>
        </ScrollArea>
      </Drawer>
    </>
  );
};

export default GameLogViewer;
