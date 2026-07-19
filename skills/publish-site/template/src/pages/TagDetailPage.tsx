import { useParams, Link } from 'react-router-dom';
import { ArrowLeft } from 'lucide-react';
import { getReportsByTag } from '@/lib/reports';
import ReportCard from '@/components/ui/ReportCard';
import Reveal from '@/components/ui/Reveal';

export default function TagDetailPage() {
  const { tag } = useParams<{ tag: string }>();
  const decodedTag = tag ? decodeURIComponent(tag) : '';
  const reports = getReportsByTag(decodedTag);

  return (
    <div className="mx-auto max-w-6xl px-6">
      <div className="py-16 md:py-20">
        <Reveal variant="fade-in" duration={500}>
          <Link
            to="/tags"
            className="mb-8 inline-flex items-center gap-1.5 text-[0.75rem] uppercase tracking-[0.15em] text-text-muted no-underline transition-colors hover:text-accent"
          >
            <ArrowLeft className="h-3.5 w-3.5" />
            返回索引
          </Link>
        </Reveal>

        <Reveal variant="fade-in" delay={80} duration={600}>
          <div className="mb-4 flex items-center gap-4">
            <div className="editorial-divider" />
            <span className="text-[0.65rem] font-semibold uppercase tracking-[0.2em] text-accent">Topic</span>
          </div>
        </Reveal>

        <Reveal variant="fade-up" delay={150} duration={700}>
          <h1 className="text-4xl text-text-bright md:text-5xl">{decodedTag}</h1>
          <p className="mt-4 text-sm text-text-secondary">共 {reports.length} 篇相关报告</p>
        </Reveal>
      </div>

      <div className="border-t border-border">
        {reports.map((report, i) => (
          <ReportCard key={report.slug} report={report} index={i} />
        ))}
      </div>

      {reports.length === 0 && (
        <div className="py-20 text-center">
          <div className="editorial-divider mx-auto mb-4" />
          <p className="font-[family-name:var(--font-family-display)] italic text-text-muted">该主题下暂无报告</p>
        </div>
      )}
    </div>
  );
}
