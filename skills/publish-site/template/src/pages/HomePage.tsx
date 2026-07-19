import HeroSection from '@/components/home/HeroSection';
import ReportGrid from '@/components/home/ReportGrid';
import { getAllReports } from '@/lib/reports';

export default function HomePage() {
  const reports = getAllReports();
  // Hero already displays the first featured report, so pass remaining ones to grid
  const featuredSlugs = reports.filter((r) => r.featured).map((r) => r.slug);
  const remainingReports = reports.filter((r) => !featuredSlugs.includes(r.slug));

  return (
    <>
      <HeroSection />
      {remainingReports.length > 0 && <ReportGrid reports={remainingReports} />}
    </>
  );
}
