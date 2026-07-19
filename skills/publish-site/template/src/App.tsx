import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { ThemeProvider } from '@/contexts/ThemeContext';
import Header from '@/components/layout/Header';
import Footer from '@/components/layout/Footer';
import HomePage from '@/pages/HomePage';
import ReportsPage from '@/pages/ReportsPage';
import ReportDetailPage from '@/pages/ReportDetailPage';
import TagsPage from '@/pages/TagsPage';
import TagDetailPage from '@/pages/TagDetailPage';

function MainLayout({ children }: { children: React.ReactNode }) {
  return (
    <>
      <Header />
      <main className="flex-1">{children}</main>
      <Footer />
    </>
  );
}

export default function App() {
  return (
    <ThemeProvider>
      <BrowserRouter>
        <Routes>
          {/* Report detail: full-screen left-right layout, no header/footer */}
          <Route path="/reports/:slug" element={<ReportDetailPage />} />

          {/* Other pages: with header + footer */}
          <Route
            path="*"
            element={
              <MainLayout>
                <Routes>
                  <Route path="/" element={<HomePage />} />
                  <Route path="/reports" element={<ReportsPage />} />
                  <Route path="/tags" element={<TagsPage />} />
                  <Route path="/tags/:tag" element={<TagDetailPage />} />
                </Routes>
              </MainLayout>
            }
          />
        </Routes>
      </BrowserRouter>
    </ThemeProvider>
  );
}
