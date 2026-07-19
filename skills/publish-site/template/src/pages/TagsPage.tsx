import { Link } from 'react-router-dom';
import { getAllTags, getReportsByTag } from '@/lib/reports';
import Reveal from '@/components/ui/Reveal';

export default function TagsPage() {
  const tags = getAllTags();

  return (
    <div className="mx-auto max-w-6xl px-6">
      <div className="py-16 md:py-20">
        <Reveal variant="fade-in" duration={600}>
          <div className="mb-4 flex items-center gap-4">
            <div className="editorial-divider" />
            <span className="text-[0.65rem] font-semibold uppercase tracking-[0.2em] text-accent">Index</span>
          </div>
        </Reveal>

        <Reveal variant="fade-up" delay={100} duration={700}>
          <h1 className="text-4xl text-text-bright md:text-5xl">主题索引</h1>
          <p className="mt-4 text-sm text-text-secondary">按主题分类浏览全部调研报告。</p>
        </Reveal>
      </div>

      <div className="border-t border-border py-12">
        <div className="grid gap-0 md:grid-cols-2 lg:grid-cols-3">
          {tags.map((tag, index) => {
            const count = getReportsByTag(tag).length;
            return (
              <Reveal variant="fade-up" delay={index * 50} key={tag}>
                <Link
                  to={`/tags/${encodeURIComponent(tag)}`}
                  className="group flex items-baseline justify-between border-b border-border px-2 py-5 no-underline transition-colors hover:bg-surface/50"
                >
                  <span className="text-base font-medium text-text-bright transition-colors group-hover:text-accent">{tag}</span>
                  <span className="font-[family-name:var(--font-family-display)] text-sm italic text-text-muted">{count} 篇</span>
                </Link>
              </Reveal>
            );
          })}
        </div>
      </div>

      {tags.length === 0 && (
        <div className="py-20 text-center">
          <div className="editorial-divider mx-auto mb-4" />
          <p className="font-[family-name:var(--font-family-display)] italic text-text-muted">暂无标签</p>
        </div>
      )}
    </div>
  );
}
