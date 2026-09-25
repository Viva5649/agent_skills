export type Report = {
  slug: string;
  title: string;
  date: string;
  summary: string;
  tags: string[];
  featured: boolean;
  htmlPath: string;
};

// Import all report JSON files statically
const reportModules = import.meta.glob('../content/reports/*.json', {
  eager: true,
}) as Record<string, { default: Report }>;

// Import all report HTML files as raw strings
const htmlModules = import.meta.glob('../../public/reports/*/index.html', {
  eager: true,
  query: '?raw',
  import: 'default',
}) as Record<string, string>;

// Build a slug -> html content map
function buildHtmlMap(): Record<string, string> {
  const map: Record<string, string> = {};
  for (const [path, content] of Object.entries(htmlModules)) {
    // path like: ../../public/reports/ai-agent-frameworks-comparison/index.html
    const match = path.match(/\/reports\/([^/]+)\/index\.html$/);
    if (match) {
      map[match[1]] = content;
    }
  }
  return map;
}

const htmlMap = buildHtmlMap();

function loadReports(): Report[] {
  return Object.values(reportModules)
    .map((mod) => mod.default ?? (mod as unknown as Report))
    .sort((a, b) => (a.date > b.date ? -1 : 1));
}

export function getAllReports(): Report[] {
  return loadReports();
}

export function getReportBySlug(slug: string): Report | undefined {
  return getAllReports().find((r) => r.slug === slug);
}

export function getReportHtml(slug: string): string | undefined {
  return htmlMap[slug];
}

export function getAllTags(): string[] {
  const all = getAllReports().flatMap((r) => r.tags);
  return [...new Set(all)];
}

export function getReportsByTag(tag: string): Report[] {
  return getAllReports().filter((r) => r.tags.includes(tag));
}

export function getFeaturedReports(): Report[] {
  return getAllReports().filter((r) => r.featured);
}
