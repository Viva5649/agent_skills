import { getAllReports } from '@/lib/reports';
import ReportCard from '@/components/ui/ReportCard';
import Reveal from '@/components/ui/Reveal';

export default function ReportsPage() {
  const reports = getAllReports();

  return (
    <div className="mx-auto max-w-6xl px-6">
      <div className="py-16 md:py-20">
        <Reveal variant="fade-in" duration={600}>
          <div className="mb-4 flex items-center gap-4">
            <div className="editorial-divider" />
            <span className="text-[0.65rem] font-semibold uppercase tracking-[0.2em] text-accent">Archives</span>
          </div>
        </Reveal>

        <Reveal variant="fade-up" delay={100} duration={700}>
          <h1 className="text-4xl text-text-bright md:text-5xl">全部档案</h1>
          <p className="mt-4 text-sm text-text-secondary">按时间倒序排列的所有深度调研报告。</p>
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
          <p className="font-[family-name:var(--font-family-display)] italic text-text-muted">暂无报告</p>
        </div>
      )}
    </div>
  );
}
