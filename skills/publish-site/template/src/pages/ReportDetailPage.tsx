import { useParams, Navigate } from 'react-router-dom';
import { getReportBySlug, getReportHtml } from '@/lib/reports';
import ReportMeta from '@/components/report/ReportMeta';
import ReportViewer from '@/components/report/ReportViewer';

export default function ReportDetailPage() {
  const { slug } = useParams<{ slug: string }>();
  const report = slug ? getReportBySlug(slug) : undefined;
  const htmlContent = slug ? getReportHtml(slug) : undefined;

  if (!report) {
    return <Navigate to="/reports" replace />;
  }

  return (
    <div className="flex flex-1 flex-col md:flex-row">
      {/* Left: Meta sidebar */}
      <aside className="w-full shrink-0 border-b border-border md:w-[380px] md:border-b-0 md:border-r lg:w-[420px]">
        <div className="sticky top-0 h-auto md:h-screen md:overflow-y-auto">
          <ReportMeta report={report} />
        </div>
      </aside>

      {/* Right: Report iframe - fills remaining height */}
      <main className="flex-1">
        <ReportViewer htmlContent={htmlContent} />
      </main>
    </div>
  );
}
