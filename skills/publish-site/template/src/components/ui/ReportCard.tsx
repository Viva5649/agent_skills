import { Link } from 'react-router-dom';
import { ArrowUpRight } from 'lucide-react';
import type { Report } from '@/lib/reports';
import Reveal from '@/components/ui/Reveal';

interface ReportCardProps {
  report: Report;
  featured?: boolean;
  index?: number;
}

// Generate a subtle gradient based on report slug for visual variety
function getCardGradient(slug: string): string {
  const gradients = [
    'from-amber-900/20 to-transparent',
    'from-indigo-900/20 to-transparent',
    'from-emerald-900/20 to-transparent',
    'from-rose-900/20 to-transparent',
    'from-cyan-900/20 to-transparent',
    'from-violet-900/20 to-transparent',
  ];
  let hash = 0;
  for (let i = 0; i < slug.length; i++) hash = slug.charCodeAt(i) + ((hash << 5) - hash);
  return gradients[Math.abs(hash) % gradients.length];
}

export default function ReportCard({ report, featured = false, index = 0 }: ReportCardProps) {
  const gradient = getCardGradient(report.slug);
  const issueNum = String(index + 1).padStart(2, '0');

  if (featured) {
    return (
      <Reveal variant="fade-up" delay={index * 80}>
        <Link to={`/reports/${report.slug}`} className="group relative block overflow-hidden border-b border-border no-underline md:border-b-0">
          {/* Gradient background */}
          <div className={`absolute inset-0 bg-gradient-to-b ${gradient} opacity-0 transition-opacity duration-500 group-hover:opacity-100`} />

          <article className="relative px-0 py-10 md:py-14">
            <div className="mb-5 flex items-center gap-5">
              {/* Large issue number with accent left border */}
              <div className="flex items-center gap-4">
                <div className="h-10 w-[2px] bg-gradient-to-b from-accent to-accent/20" />
                <span className="font-[family-name:var(--font-family-display)] text-4xl font-light text-text-muted/25 md:text-6xl">{issueNum}</span>
              </div>
              <div className="flex flex-col gap-1">
                <span className="text-[0.65rem] font-semibold uppercase tracking-[0.2em] text-text-muted">{report.date}</span>
                <div className="editorial-divider" />
              </div>
            </div>

            <h2 className="text-2xl font-bold leading-snug tracking-tight text-text-bright transition-colors group-hover:text-accent md:text-3xl lg:text-4xl">
              {report.title}
            </h2>

            <p className="mt-4 max-w-2xl text-sm leading-relaxed text-text-secondary">{report.summary}</p>

            <div className="mt-6 flex items-center gap-4">
              {report.tags.map((tag) => (
                <span key={tag} className="text-[0.65rem] uppercase tracking-[0.15em] text-text-muted">
                  #{tag}
                </span>
              ))}
            </div>

            {/* Bottom accent gradient line */}
            <div className="mt-8 h-px w-full bg-gradient-to-r from-accent/40 via-accent/10 to-transparent" />
          </article>
        </Link>
      </Reveal>
    );
  }

  return (
    <Reveal variant="fade-up" delay={index * 60}>
      <Link
        to={`/reports/${report.slug}`}
        className="group relative block border-b border-border py-8 no-underline transition-colors last:border-b-0 hover:bg-surface/50"
      >
        {/* Left accent indicator on hover */}
        <div className="absolute left-0 top-0 h-full w-[2px] origin-top scale-y-0 bg-accent transition-transform duration-300 group-hover:scale-y-100" />

        <article className="flex items-start gap-6 pl-4">
          {/* Issue number as decorative background */}
          <div className="relative hidden md:block">
            <span className="font-[family-name:var(--font-family-display)] text-3xl font-light text-text-muted/10 transition-colors duration-300 group-hover:text-accent/15">
              {issueNum}
            </span>
          </div>

          <div className="flex-1">
            <div className="mb-2 flex items-center gap-3">
              <span className="text-[0.65rem] text-text-muted">{report.date}</span>
              <span className="text-text-muted/30">·</span>
              {report.tags.slice(0, 2).map((tag) => (
                <span key={tag} className="text-[0.65rem] uppercase tracking-[0.1em] text-text-muted">
                  {tag}
                </span>
              ))}
            </div>

            <h3 className="text-lg font-bold leading-snug text-text-bright transition-colors group-hover:text-accent">{report.title}</h3>

            <p className="mt-2 line-clamp-2 text-sm leading-relaxed text-text-secondary">{report.summary}</p>
          </div>

          <ArrowUpRight className="mt-1 h-5 w-5 flex-shrink-0 text-text-muted opacity-0 transition-all duration-300 group-hover:opacity-100 group-hover:text-accent" />
        </article>
      </Link>
    </Reveal>
  );
}
