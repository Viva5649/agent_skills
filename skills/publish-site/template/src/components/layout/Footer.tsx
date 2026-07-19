import Reveal from '@/components/ui/Reveal';

export default function Footer() {
  return (
    <footer className="mt-auto border-t border-border">
      <div className="mx-auto max-w-6xl px-6 py-16">
        <Reveal variant="fade-up" duration={700}>
          <div className="grid gap-12 md:grid-cols-3">
            {/* Brand */}
            <div>
              <h3 className="text-xl text-text-bright">Vantage</h3>
              <p className="mt-3 text-sm leading-relaxed text-text-muted">
                汇集各领域前沿动态的深度调研报告，
                <br />
                以杂志级的品质呈现技术洞察。
              </p>
            </div>

            {/* Links */}
            <div>
              <div className="mb-3 text-[0.65rem] font-semibold uppercase tracking-[0.2em] text-text-muted">导航</div>
              <div className="flex flex-col gap-2">
                <a href="/" className="text-sm text-text-secondary no-underline transition-colors hover:text-accent">
                  首页
                </a>
                <a href="/reports" className="text-sm text-text-secondary no-underline transition-colors hover:text-accent">
                  档案
                </a>
                <a href="/tags" className="text-sm text-text-secondary no-underline transition-colors hover:text-accent">
                  索引
                </a>
              </div>
            </div>

            {/* Info */}
            <div>
              <div className="mb-3 text-[0.65rem] font-semibold uppercase tracking-[0.2em] text-text-muted">关于</div>
              <p className="text-sm leading-relaxed text-text-secondary">Vantage 是一个独立研究项目， 专注于深度调研与分析。</p>
            </div>
          </div>
        </Reveal>

        <Reveal variant="fade-in" delay={200} duration={600}>
          <div className="mt-16 flex items-center justify-between border-t border-border pt-8">
            <span className="text-xs tracking-wider text-text-muted">&copy; {new Date().getFullYear()} Vantage</span>
            <span className="issue-label text-xs">Vol. 01</span>
          </div>
        </Reveal>
      </div>
    </footer>
  );
}
