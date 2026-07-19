import { useMemo } from 'react';
import { useTheme } from '@/contexts/ThemeContext';

interface ReportViewerProps {
  htmlContent?: string;
}

/** Inject a `data-theme` attribute into an HTML string's <html> tag only. */
export function injectTheme(html: string, theme: string): string {
  return html.replace(/<html([^>]*)>/i, (_match, attrs: string) => {
    const cleaned = attrs.replace(/\s*data-theme="[^"]*"/i, '');
    return `<html${cleaned} data-theme="${theme}">`;
  });
}

export default function ReportViewer({ htmlContent }: ReportViewerProps) {
  const { theme } = useTheme();

  const themedHtml = useMemo(() => {
    if (!htmlContent) return undefined;
    return injectTheme(htmlContent, theme);
  }, [htmlContent, theme]);

  return (
    <div className="relative h-[calc(100vh-64px)] w-full p-1.5 md:h-screen md:p-2">
      <div className="relative h-full">
        {/* Decorative multi-layer frame */}
        <div className="pointer-events-none absolute inset-0 z-10" aria-hidden="true">
          {/* Layer 1: outer heavy border */}
          <div className="absolute inset-0 border-[2.5px] border-accent/55" />

          {/* Layer 2: outer fine rule */}
          <div className="absolute inset-[4px] border-[0.5px] border-accent/25" />

          {/* Breathing space */}

          {/* Layer 3: inner fine rule */}
          <div className="absolute inset-[9px] border-[0.5px] border-accent/25" />

          {/* Layer 4: inner heavy border */}
          <div className="absolute inset-[11px] border-[1.8px] border-accent/50" />

          {/* Corner anchors */}
          <div className="absolute left-0 top-0 h-[14px] w-[14px] border-b-0 border-r-0 border-[2.5px] border-accent/55" />
          <div className="absolute right-0 top-0 h-[14px] w-[14px] border-b-0 border-l-0 border-[2.5px] border-accent/55" />
          <div className="absolute bottom-0 left-0 h-[14px] w-[14px] border-t-0 border-r-0 border-[2.5px] border-accent/55" />
          <div className="absolute bottom-0 right-0 h-[14px] w-[14px] border-t-0 border-l-0 border-[2.5px] border-accent/55" />
        </div>

        {/* Content area with inset depth */}
        <div className="absolute inset-[14px] overflow-hidden bg-surface-elevated shadow-[inset_0_0_12px_rgba(0,0,0,0.06)]">
          {themedHtml ? (
            <iframe key={theme} srcDoc={themedHtml} className="block h-full w-full border-0" title="Report Content" />
          ) : (
            <div className="flex h-full items-center justify-center text-text-muted">
              <p className="font-[family-name:var(--font-family-display)] italic">报告内容加载失败</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
