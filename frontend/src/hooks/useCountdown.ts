import { useEffect, useRef, useState } from "react";
import { createCountdown } from "../../js/deadline.js";

export function useCountdown(expiresAt: string, onElapsed: () => void) {
  const callback = useRef(onElapsed);
  callback.current = onElapsed;
  const [text, setText] = useState("");
  useEffect(() => {
    const timer = createCountdown({
      expiresAtIso: expiresAt,
      onTick: setText,
      onElapsed: () => {
        setText("Time elapsed.");
        callback.current();
      },
    });
    return () => timer.stop();
  }, [expiresAt]);
  return text;
}
