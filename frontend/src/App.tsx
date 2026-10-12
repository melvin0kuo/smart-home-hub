import { useCallback, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "./services/api";
import type { Session } from "./types/device";
import { Dashboard } from "./pages/Dashboard";
import { Login } from "./pages/Login";
export default function App() {
  const queryClient = useQueryClient(),
    [manual, setManual] = useState<Session | null>(null);
  const me = useQuery({
    queryKey: ["session"],
    queryFn: api.me,
    retry: false,
    refetchOnWindowFocus: false,
  });
  const logout = useCallback(() => {
    setManual(null);
    queryClient.setQueryData(["session"], null);
  }, [queryClient]);
  if (me.isPending && !manual)
    return <div className="boot">正在連接你的家庭平台…</div>;
  const session = manual ?? me.data;
  return session ? (
    <Dashboard session={session} onLogout={logout} />
  ) : (
    <Login
      onLogin={(s) => {
        setManual(s);
        queryClient.setQueryData(["session"], s);
      }}
    />
  );
}
