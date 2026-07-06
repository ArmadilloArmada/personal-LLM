export function renderTemplate(
  template: string,
  context: Record<string, unknown>
): string {
  return template.replace(/\{\{([\w.]+)\}\}/g, (_, path: string) => {
    const value = getPath(context, path);
    if (value === undefined || value === null) return '';
    if (typeof value === 'object') return JSON.stringify(value);
    return String(value);
  });
}

function getPath(obj: Record<string, unknown>, path: string): unknown {
  return path.split('.').reduce<unknown>((acc, key) => {
    if (acc && typeof acc === 'object' && key in (acc as Record<string, unknown>)) {
      return (acc as Record<string, unknown>)[key];
    }
    return undefined;
  }, obj);
}
