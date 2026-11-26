import { EMAIL, LETTER_DIGIT, RAW_CLASS } from "./username-policy-data.js";

const rawPattern = new RegExp(`^[${RAW_CLASS}]+(?![\\s\\S])`, "u");
const startPattern = new RegExp(`^[${LETTER_DIGIT}]`, "u");
const plainPattern = new RegExp(`^[${LETTER_DIGIT}][${LETTER_DIGIT}_.+-]*(?![\\s\\S])`, "u");
const emailPattern = new RegExp(`^${EMAIL}(?![\\s\\S])`, "u");

export function registrationUsernameError(raw) {
  if (!raw) return "Account ID is required.";
  if (!rawPattern.test(raw)) {
    return "Account ID contains a space, invisible character, or unsupported character.";
  }
  if (!startPattern.test(raw)) {
    return "Start with a letter or digit and use only letters, digits, _, -, ., or +.";
  }
  const value = raw.normalize("NFKC");
  if ([...value].length > 60) return "Account ID must be at most 60 characters after normalization.";
  if (value.includes("@")) {
    return emailPattern.test(value) ? "" : "Enter a valid email address to use as your account ID.";
  }
  return plainPattern.test(value) ? "" : "Start with a letter or digit and use only letters, digits, _, -, ., or +.";
}
