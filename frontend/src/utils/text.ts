const CONTROL_CHARS = /[\u0000-\u0008\u000b\u000c\u000e-\u001f\u007f-\u009f\u00A0\u200B-\u200F\u2028\u2029]+/g;
const XML_NOISE =
  /\b(?:xmlformats\.org|schemaRefs|datastoreItem|WordDocument|MsoDataStore|Microsoft Office Word|mc:Ignorable|w:rsid\w+)\b/gi;

export function displayText(value: string | null | undefined, fallback = "未命名") {
  const cleaned = String(value || "")
    .replace(CONTROL_CHARS, " ")
    .replace(XML_NOISE, " ")
    .replace(/\r\n?/g, "\n")
    .replace(/[ \t]{2,}/g, " ")
    .replace(/\n{3,}/g, "\n\n")
    .trim();
  return cleaned || fallback;
}

export function previewText(value: string | null | undefined, maxLength = 220, fallback = "暂无内容") {
  const cleaned = displayText(value, fallback);
  return cleaned.length > maxLength ? `${cleaned.slice(0, maxLength)}...` : cleaned;
}
