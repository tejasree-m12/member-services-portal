import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { api, onUnauthorized, setToken, tokenStore } from "../api/client.js";

// React Context makes the signed-in user available to every component
// without passing it down through props at every level.
const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  // "checking" is true while we ask the server whether a saved token is still valid.
  const [checking, setChecking] = useState(Boolean(tokenStore.get()));

  const logout = useCallback(() => {
    setToken(null);
    setUser(null);
  }, []);

  useEffect(() => {
    onUnauthorized(logout);
    if (!tokenStore.get()) return;
    api
      .get("/auth/me")
      .then((data) => setUser(data.user))
      .catch(() => logout())
      .finally(() => setChecking(false));
  }, [logout]);

  const login = useCallback(async (email, password) => {
    const data = await api.post("/auth/login", { email, password });
    setToken(data.access_token);
    setUser(data.user);
  }, []);

  const value = useMemo(
    () => ({
      user,
      checking,
      login,
      logout,
      // These only decide what the UI shows. The server checks permissions
      // again on every request; hiding a button is not security.
      canEdit: user ? ["admin", "agent"].includes(user.role) : false,
      isAdmin: user ? user.role === "admin" : false,
    }),
    [user, checking, login, logout]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const value = useContext(AuthContext);
  if (!value) throw new Error("useAuth must be used inside <AuthProvider>");
  return value;
}
