import { lazy, Suspense } from "react";
import { Link, Route, Routes } from "react-router-dom";
import { useTranslation } from "react-i18next";
import Layout from "./components/Layout";
import Citizen from "./pages/Citizen";
import Verify from "./pages/Verify";
import { Loading } from "./components/QueryState";
import { usePageTitle } from "./hooks/usePageTitle";

// Reviewer pages pull in Recharts; load them on demand so the citizen page stays light on mobile.
const ReviewerDashboard = lazy(() => import("./pages/ReviewerDashboard"));
const BoothDetail = lazy(() => import("./pages/BoothDetail"));

function NotFound() {
  const { t } = useTranslation();
  usePageTitle(t("not_found.title"));
  return (
    <section>
      <h1 className="text-2xl font-bold">{t("not_found.title")}</h1>
      <Link
        to="/"
        className="mt-2 inline-flex min-h-11 items-center text-blue-800 underline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-700"
      >
        {t("not_found.back")}
      </Link>
    </section>
  );
}

/** Route table. Providers (router, query client) are set up in main.tsx / tests. */
export default function App() {
  return (
    <Suspense fallback={<Loading />}>
      <Routes>
        <Route element={<Layout />}>
          <Route path="/" element={<Citizen />} />
          <Route path="/reviewer" element={<ReviewerDashboard />} />
          <Route path="/reviewer/booth/:part" element={<BoothDetail />} />
          <Route path="/verify" element={<Verify />} />
          <Route path="*" element={<NotFound />} />
        </Route>
      </Routes>
    </Suspense>
  );
}
