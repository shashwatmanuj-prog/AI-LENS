// Device-local list of analyses the person has opened. Not an account system:
// it only remembers ids so the Saved page can fetch summaries.

const KEY = "communitylens:saved";
const MAX = 50;

export function getSavedIds(): string[] {
  try {
    const raw = window.localStorage.getItem(KEY);
    const ids = raw ? JSON.parse(raw) : [];
    return Array.isArray(ids) ? ids.filter((x) => typeof x === "string") : [];
  } catch {
    return [];
  }
}

export function rememberAnalysis(id: string) {
  try {
    const ids = [id, ...getSavedIds().filter((x) => x !== id)].slice(0, MAX);
    window.localStorage.setItem(KEY, JSON.stringify(ids));
  } catch {
    /* storage unavailable (private mode); saving is a convenience only */
  }
}

export function checklistKey(analysisId: string) {
  return `communitylens:checklist:${analysisId}`;
}

export function readChecklist(analysisId: string): string[] {
  try {
    const raw = window.localStorage.getItem(checklistKey(analysisId));
    return raw ? JSON.parse(raw) : [];
  } catch {
    return [];
  }
}

export function writeChecklist(analysisId: string, done: string[]) {
  try {
    window.localStorage.setItem(checklistKey(analysisId), JSON.stringify(done));
  } catch {
    /* ignore */
  }
}
