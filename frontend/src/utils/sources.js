/**
 * Groups a flat list of {file_name, page} source citations into one entry
 * per file, with all its cited pages collected and sorted. This is what
 * turns 6 separate "CSS Notes.pdf · p.1" / "CSS Notes.pdf · p.3" / ... tags
 * into a single "CSS Notes.pdf · p.1, 3, 14" tag.
 */
export function groupSourcesByFile(sources) {
  if (!sources || sources.length === 0) return [];

  const pagesByFile = new Map();
  for (const { file_name, page } of sources) {
    if (!pagesByFile.has(file_name)) {
      pagesByFile.set(file_name, new Set());
    }
    pagesByFile.get(file_name).add(page);
  }

  return Array.from(pagesByFile.entries()).map(([file_name, pageSet]) => ({
    file_name,
    pages: Array.from(pageSet).sort((a, b) => a - b),
  }));
}
