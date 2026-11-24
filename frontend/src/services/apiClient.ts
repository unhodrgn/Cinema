import { getApi } from "../../js/api.js";
import { getAuth } from "../../js/auth.js";
import type { User } from "../types/cinema";

export const auth = getAuth() as {
  currentUser(): Promise<User | null>;
  login(name: string, password: string): Promise<User>;
  register(name: string, password: string): Promise<User>;
  logout(): Promise<void>;
};
export function get<T>(path: string): Promise<T> {
  const separator = path.indexOf("?");
  if (separator < 0) return getApi().get(path);
  const query = Object.fromEntries(
    new URLSearchParams(path.slice(separator + 1)),
  );
  return getApi().get(path.slice(0, separator), { query });
}
export function post<T>(path: string, body: object = {}): Promise<T> {
  return getApi().post(path, body);
}
export function errorMessage(error: unknown) {
  return error instanceof Error
    ? error.message
    : "The request could not be completed.";
}
