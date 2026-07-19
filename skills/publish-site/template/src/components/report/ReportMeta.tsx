import { Calendar, ExternalLink, ArrowLeft } from 'lucide-react';
import { Link } from 'react-router-dom';
import type { Report } from '@/lib/reports';
import { getReportHtml } from '@/lib/reports';
import ThemeToggle from '@/components/ui/ThemeToggle';
import { useTheme } from '@/contexts/ThemeContext';
import { injectTheme } from '@/components/report/ReportViewer';

interface ReportMetaProps {
  report: Report;
}

export default function ReportMeta({ report }: ReportMetaProps) {
  const { theme } = useTheme();

  return (
    <div className="flex h-full flex-col px-8 py-10 md:py-12">
      {/* Breadcrumb */}
      <div className="mb-10 flex items-center justify-between">
        <Link
          to="/reports"
          className="inline-flex items-center gap-1.5 text-[0.75rem] uppercase tracking-[0.15em] text-text-muted no-underline transition-colors hover:text-accent"
        >
          <ArrowLeft className="h-3.5 w-3.5" />
          返回档案
        </Link>
        <ThemeToggle />
      </div>

      {/* Label */}
      <div className="mb-5 flex items-center gap-4">
        <div className="editorial-divider" />
        <span className="text-[0.65rem] font-semibold uppercase tracking-[0.2em] text-accent">深度调研</span>
      </div>

      {/* Title */}
      <h1 className="text-2xl font-bold leading-tight text-text-bright lg:text-3xl">{report.title}</h1>

      {/* Summary */}
      <p className="mt-5 text-sm leading-relaxed text-text-secondary">{report.summary}</p>

      {/* Divider */}
      <div className="my-8 h-px w-full bg-border" />

      {/* Meta info */}
      <div className="space-y-6">
        <div>
          <div className="mb-1.5 text-[0.6rem] font-semibold uppercase tracking-[0.2em] text-text-muted">发布日期</div>
          <div className="flex items-center gap-2 text-sm text-text-primary">
            <Calendar className="h-3.5 w-3.5 text-text-muted" />
            {report.date}
          </div>
        </div>

        <div>
          <div className="mb-2 text-[0.6rem] font-semibold uppercase tracking-[0.2em] text-text-muted">标签</div>
          <div className="flex flex-wrap gap-2">
            {report.tags.map((tag) => (
              <Link
                key={tag}
                to={`/tags/${encodeURIComponent(tag)}`}
                className="text-[0.7rem] uppercase tracking-[0.12em] text-text-secondary no-underline transition-colors hover:text-accent"
              >
                #{tag}
              </Link>
            ))}
          </div>
        </div>
      </div>

      {/* Actions - pushed to bottom */}
      <div className="mt-auto pt-8">
        <button
          onClick={() => {
            const html = getReportHtml(report.slug);
            if (html) {
              const themed = injectTheme(html, theme);
              const blob = new Blob([themed], { type: 'text/html' });
              window.open(URL.createObjectURL(blob), '_blank');
            }
          }}
          className="inline-flex items-center gap-2 border-t border-border pt-6 text-[0.75rem] font-medium uppercase tracking-[0.12em] text-text-muted transition-colors hover:text-accent cursor-pointer"
        >
          <ExternalLink className="h-3.5 w-3.5" />
          独立窗口打开
        </button>
      </div>
    </div>
  );
}
