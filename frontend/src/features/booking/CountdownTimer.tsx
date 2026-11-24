import { useCountdown } from "../../hooks/useCountdown";
export function CountdownTimer({
  expiresAt,
  onElapsed,
}: {
  expiresAt: string;
  onElapsed: () => void;
}) {
  return <p className="countdown">{useCountdown(expiresAt, onElapsed)}</p>;
}
