// Display formatting for values that come from the API. Pure functions, no business rules.
//
// Times: the API sends ISO 8601 strings with the cinema's own UTC offset (for example
// "2026-11-25T19:00:00+09:00", API contract section 4). They are shown exactly as written, so
// the page reads the same in every browser time zone. There is deliberately no `Date` and no
// `Intl` here: converting to the viewer's zone would show other people's local time.
//
// Money: decimal strings ("12000.00"); never converted to a floating-point number. Amounts are
// Korean won, shown with the ₩ sign in front ("₩12,000").
export const CURRENCY_SIGN = "₩";

const ISO_DATE_TIME = /^(\d{4}-\d{2}-\d{2})T(\d{2}:\d{2})/;
const DECIMAL = /^(-?)(\d+)(?:\.(\d+))?$/;

/** "12000.00" -> "₩12,000"; "9500.50" -> "₩9,500.50"; "-5.25" -> "-₩5.25"; anything else -> "". */
export function formatMoney(value) {
  const match = DECIMAL.exec(typeof value === "string" ? value.trim() : "");
  if (!match) return "";
  const [, sign, whole, fraction = ""] = match;
  const grouped = whole.replace(/\B(?=(\d{3})+(?!\d))/g, ",");
  const kept = /^0*$/.test(fraction) ? "" : `.${fraction}`;
  return `${sign}${CURRENCY_SIGN}${grouped}${kept}`;
}

/** "2026-11-25T19:00:00+09:00" -> "2026-11-25 19:00" (as written); invalid -> "". */
export function formatDateTime(value) {
  const match = ISO_DATE_TIME.exec(typeof value === "string" ? value : "");
  return match ? `${match[1]} ${match[2]}` : "";
}

/** The date part: "2026-11-25". */
export function formatDate(value) {
  const match = ISO_DATE_TIME.exec(typeof value === "string" ? value : "");
  return match ? match[1] : "";
}

/** The clock part: "19:00". */
export function formatTime(value) {
  const match = ISO_DATE_TIME.exec(typeof value === "string" ? value : "");
  return match ? match[2] : "";
}

/** "19:00 - 21:00" for a start and an end timestamp. */
export function formatTimeRange(start, end) {
  const from = formatTime(start);
  const to = formatTime(end);
  return from && to ? `${from} - ${to}` : from;
}

/**
 * "2026-11-25 19:00 - 21:00" (date once, as written). When the end falls on another day the end
 * carries its own date: "2026-11-25 23:30 - 2026-11-26 01:10". A missing or invalid end gives only the start.
 */
export function formatDateTimeRange(start, end) {
  const from = formatDateTime(start);
  if (!from) return "";
  if (!formatTime(end)) return from;
  return formatDate(end) === formatDate(start) ? `${from} - ${formatTime(end)}` : `${from} - ${formatDateTime(end)}`;
}

/** "120 min". */
export function formatDuration(minutes) {
  return Number.isInteger(minutes) && minutes > 0 ? `${minutes} min` : "";
}

/** True for a string made only of digits that is a usable id ("3", not "0", "03x", "-1"). */
export function isIdText(value) {
  return typeof value === "string" && /^[1-9][0-9]{0,18}$/.test(value);
}

/** True for "YYYY-MM-DD" (shape only; the server decides whether the date exists). */
export function isDateText(value) {
  return typeof value === "string" && /^\d{4}-\d{2}-\d{2}$/.test(value);
}
