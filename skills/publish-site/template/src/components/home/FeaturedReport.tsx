import { getFeaturedReports } from '@/lib/reports';
import ReportCard from '@/components/ui/ReportCard';

export default function FeaturedReport() {
  const featured = getFeaturedReports();

  if (featured.length === 0) return null;

  return (
    <section className="border-b border-border">
      <div className="mx-auto max-w-6xl px-6">
        <div className="py-6">
          <div className="flex items-center gap-4">
            <div className="editorial-divider" />
            <span className="text-[0.65rem] font-semibold uppercase tracking-[0.2em] text-text-muted">精选专题</span>
          </div>
        </div>

        <div className="divide-y divide-border">
          {featured.map((report, i) => (
            <ReportCard key={report.slug} report={report} featured index={i} />
          ))}
        </div>
      </div>
    </section>
  );
}
