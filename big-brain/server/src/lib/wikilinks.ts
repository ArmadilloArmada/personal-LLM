export const WIKILINK_REGEX = /\[\[([^\]|]+)(?:\|([^\]]+))?\]\]/g;
export const TAG_REGEX = /(?:^|\s)#([a-zA-Z][\w-]*)/g;

export function extractWikilinks(content: string): string[] {
  const links = new Set<string>();
  let match: RegExpExecArray | null;
  const re = new RegExp(WIKILINK_REGEX.source, 'g');
  while ((match = re.exec(content)) !== null) {
    links.add(match[1].trim());
  }
  return [...links];
}

export function extractTags(content: string): string[] {
  const tags = new Set<string>();
  let match: RegExpExecArray | null;
  const re = new RegExp(TAG_REGEX.source, 'g');
  while ((match = re.exec(content)) !== null) {
    tags.add(match[1].toLowerCase());
  }
  return [...tags];
}

export function titleFromPath(path: string): string {
  const base = path.split('/').pop() ?? path;
  return base.replace(/\.md$/i, '').replace(/-/g, ' ');
}

export function slugToPath(slug: string): string {
  const normalized = slug.trim();
  if (normalized.endsWith('.md')) return normalized;
  return `${normalized}.md`;
}

export function resolveLinkTarget(target: string, allPaths: string[]): string | null {
  const normalized = target.trim();
  const candidates = allPaths.filter((p) => {
    const name = p.split('/').pop()?.replace(/\.md$/i, '') ?? '';
    return (
      p === normalized ||
      p === `${normalized}.md` ||
      name.toLowerCase() === normalized.toLowerCase() ||
      p.toLowerCase() === `${normalized.toLowerCase()}.md`
    );
  });
  return candidates[0] ?? null;
}
