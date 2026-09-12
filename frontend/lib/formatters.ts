/**
 * Format a number into standard Pakistani numbering format (Lakhs and Crores).
 * Example: 2500000 -> "25,00,000.00"
 */
export function formatPKR(val: number | string | undefined | null): string {
  if (val === undefined || val === null || val === "") return "PKR 0.00";
  const num = typeof val === "string" ? parseFloat(val.replace(/,/g, "")) : val;
  if (isNaN(num)) return "PKR 0.00";

  const isNegative = num < 0;
  const absNum = Math.abs(num);
  const parts = absNum.toFixed(2).split(".");
  let intPart = parts[0];
  const decPart = parts[1];

  // Pakistani grouping: last 3 digits, then groups of 2 digits
  if (intPart.length > 3) {
    const last3 = intPart.substring(intPart.length - 3);
    const rest = intPart.substring(0, intPart.length - 3);
    const groups: string[] = [];
    let cur = rest;
    while (cur.length > 2) {
      groups.unshift(cur.substring(cur.length - 2));
      cur = cur.substring(0, cur.length - 2);
    }
    if (cur.length > 0) {
      groups.unshift(cur);
    }
    intPart = groups.join(",") + "," + last3;
  }

  return `${isNegative ? "-" : ""}PKR ${intPart}.${decPart}`;
}

export function formatDatePKT(dateStr?: string | null): string {
  if (!dateStr) return "—";
  try {
    const d = new Date(dateStr);
    return new Intl.DateTimeFormat("en-PK", {
      year: "numeric",
      month: "short",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
      hour12: false,
    }).format(d);
  } catch {
    return dateStr;
  }
}

export function truncateHash(hash?: string | null, len = 12): string {
  if (!hash) return "—";
  if (hash.length <= len * 2) return hash;
  return `${hash.substring(0, len)}...${hash.substring(hash.length - len)}`;
}
