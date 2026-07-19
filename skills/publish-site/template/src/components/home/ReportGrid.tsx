import { getAllReports, type Report } from '@/lib/reports';
import ReportCard from '@/components/ui/ReportCard';

interface ReportGridProps {
  reports?: Report[];
}

export default function ReportGrid({ reports }: ReportGridProps) {
  const displayReports = reports ?? getAllReports();

  if (displayReports.length === 0) return null;

  return (
    <section>
      <div className="mx-auto max-w-6xl px-6">
        <div className="py-6">
          <div className="flex items-center gap-4">
            <div className="editorial-divider" />
            <span className="text-[0.65rem] font-semibold uppercase tracking-[0.2em] text-text-muted">更多报告</span>
          </div>
        </div>

        <div>
          {displayReports.map((report, i) => (
            <ReportCard key={report.slug} report={report} index={i} />
          ))}
        </div>
      </div>
    </section>
  );
}
