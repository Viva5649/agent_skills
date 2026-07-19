import { getFeaturedReports } from '@/lib/reports';
import { Link } from 'react-router-dom';
import { ArrowRight } from 'lucide-react';
import Reveal from '@/components/ui/Reveal';

export default function HeroSection() {
  const featured = getFeaturedReports();
  const hero = featured[0];

  return (
    <section className="relative border-b border-border overflow-hidden">
      {/* Ambient glow */}
      <div className="pointer-events-none absolute inset-0" aria-hidden="true">
        <div className="absolute left-[-10%] top-[10%] h-[500px] w-[600px] rounded-full bg-[radial-gradient(ellipse,rgba(139,105,20,0.06),transparent_70%)] blur-2xl dark:bg-[radial-gradient(ellipse,rgba(200,169,126,0.07),transparent_70%)]" />
        <div className="absolute right-[-5%] bottom-[5%] h-[300px] w-[400px] rounded-full bg-[radial-gradient(ellipse,rgba(139,105,20,0.03),transparent_70%)] blur-3xl dark:bg-[radial-gradient(ellipse,rgba(200,169,126,0.04),transparent_70%)]" />
      </div>
      <div className="relative mx-auto max-w-6xl px-6">
        {/* Magazine masthead area */}
        <div className="py-20 md:py-28">
          <div className="grid items-end gap-12 md:grid-cols-12">
            {/* Left - Big editorial headline */}
            <div className="md:col-span-7">
              <Reveal variant="fade-in" duration={600}>
                <div className="mb-6 flex items-center gap-4">
                  <div className="editorial-divider" />
                  <span className="text-[0.7rem] font-semibold uppercase tracking-[0.2em] text-accent">本期专题</span>
                </div>
              </Reveal>

              {hero ? (
                <>
                  <Reveal variant="fade-up" delay={100} duration={800}>
                    <Link to={`/reports/${hero.slug}`} className="group block no-underline">
                      <h1 className="text-[clamp(2rem,4.5vw,3.8rem)] font-bold leading-[1.1] text-text-bright transition-colors group-hover:text-accent">
                        {hero.title}
                      </h1>
                    </Link>
                  </Reveal>

                  <Reveal variant="fade-up" delay={250} duration={800}>
                    <p className="mt-6 max-w-lg text-base leading-relaxed text-text-secondary">{hero.summary}</p>
                  </Reveal>

                  <Reveal variant="fade-up" delay={400} duration={700}>
                    <Link to={`/reports/${hero.slug}`} className="group mt-8 inline-flex items-center gap-2 no-underline">
                      <span className="text-sm font-medium tracking-wide text-accent transition-colors">阅读全文</span>
                      <ArrowRight className="h-4 w-4 text-accent transition-transform group-hover:translate-x-1" />
                    </Link>

                    <div className="mt-6 flex flex-wrap gap-3">
                      {hero.tags.map((tag) => (
                        <Link
                          key={tag}
                          to={`/tags/${encodeURIComponent(tag)}`}
                          className="text-[0.7rem] uppercase tracking-[0.15em] text-text-muted no-underline transition-colors hover:text-accent"
                        >
                          #{tag}
                        </Link>
                      ))}
                    </div>
                  </Reveal>
                </>
              ) : (
                <Reveal variant="fade-up" delay={100} duration={800}>
                  <h1 className="text-[clamp(2rem,4.5vw,3.8rem)] font-bold leading-[1.1] text-text-bright">
                    深度技术调研
                    <br />
                    与前沿洞察
                  </h1>
                </Reveal>
              )}
            </div>

            {/* Right - Editorial aside */}
            <div className="md:col-span-5">
              <Reveal variant="slide-right" delay={350} duration={800}>
                <div className="border-l border-border-strong pl-8">
                  <span className="issue-label text-sm">编者按</span>
                  <p className="mt-4 font-[family-name:var(--font-family-display)] text-lg leading-relaxed text-text-secondary italic">
                    "在信息与技术日新月异的时代，我们致力于以冷静的研究视角， 为你提供最深度的对比评测与洞察分析。"
                  </p>
                  <div className="mt-6 flex items-center gap-3">
                    <div className="flex h-8 w-8 items-center justify-center rounded-full border border-border-strong bg-surface-elevated">
                      <svg
                        viewBox="0 0 24 24"
                        fill="none"
                        className="h-4 w-4 text-accent"
                        stroke="currentColor"
                        strokeWidth="1.5"
                        strokeLinecap="round"
                        strokeLinejoin="round"
                      >
                        <path d="M12 3L20 7.5V16.5L12 21L4 16.5V7.5L12 3Z" />
                        <path d="M12 12L20 7.5" />
                        <path d="M12 12V21" />
                        <path d="M12 12L4 7.5" />
                      </svg>
                    </div>
                    <div>
                      <div className="text-xs font-medium text-text-primary">Vantage</div>
                      <div className="text-[0.65rem] text-text-muted">编辑部</div>
                    </div>
                  </div>
                </div>
              </Reveal>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
