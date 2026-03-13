import { useIsFetching, useIsMutating } from "@tanstack/react-query";
import { useEffect } from "react";

/**
 * GlobalCursor component
 *
 * Automatically changes the browser cursor to 'progress' whenever
 * there are active background fetches or mutations occurring via TanStack Query.
 */
const GlobalCursor = () => {
  const isFetching = useIsFetching();
  const isMutating = useIsMutating();
  const isLoading = isFetching > 0 || isMutating > 0;

  useEffect(() => {
    if (isLoading) {
      document.documentElement.style.cursor = "wait";
    } else {
      document.documentElement.style.cursor = "default";
    }
  }, [isLoading]);

  return null;
};

export default GlobalCursor;
