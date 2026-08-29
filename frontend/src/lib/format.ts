/** Normalizes messy source phone strings (e.g. "(+99855) 5080249", "71 2345334")
 * into a consistent "+998 XX XXX-XX-XX" display format. Purely presentational --
 * the raw value stored in the database is never changed, this only affects how
 * it's shown. Falls back to the original text when a number doesn't cleanly
 * decompose into a 9-digit Uzbek subscriber number, rather than guessing wrong. */
export function formatPhone(raw: string | null | undefined): string {
  if (!raw) return "—";

  return raw
    .split(",")
    .map((part) => formatSingle(part.trim()))
    .join(", ");
}

/** Split a raw phone field into individually callable numbers.
 *
 *  Sources routinely pack several numbers into one string ("(+99871) 2301650,
 *  (+99871) 2309007"), and an operator dialling from the screen needs one at a
 *  time -- both to tap and to copy. `display` is what the human reads, `dial` is
 *  the E.164-ish form a tel: link needs. Entries that do not decompose cleanly
 *  are kept with `dial: null` rather than guessing a wrong number. */
export function splitPhones(raw: string | null | undefined): { display: string; dial: string | null }[] {
  if (!raw) return [];
  return raw
    .split(",")
    .map((p) => p.trim())
    .filter((p) => p && p.toLowerCase() !== "null")
    .map((part) => {
      let digits = part.replace(/\D/g, "");
      if (digits.length === 12 && digits.startsWith("998")) digits = digits.slice(3);
      const dial = digits.length === 9 ? `+998${digits}` : null;
      return { display: formatSingle(part), dial };
    });
}

function formatSingle(part: string): string {
  let digits = part.replace(/\D/g, "");
  if (digits.length === 12 && digits.startsWith("998")) {
    digits = digits.slice(3);
  } else if (digits.length !== 9) {
    return part; // doesn't match the expected Uzbek shape -- show as-is rather than mangle it
  }

  const operatorCode = digits.slice(0, 2);
  const number = digits.slice(2);
  return `+998 ${operatorCode} ${number.slice(0, 3)}-${number.slice(3, 5)}-${number.slice(5, 7)}`;
}
