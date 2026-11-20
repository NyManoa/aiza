import { lazy, type ReactElement, Suspense } from "react";
import { createBrowserRouter } from "react-router";

import { Loading } from "../components/Feedback";
import { PlannerPage } from "../features/planner/PlannerPage";
import { Layout } from "./Layout";
import { RouteError } from "./RouteError";

// Pages secondaires chargées à la demande (code splitting).
const AnalysisPage = lazy(() => import("../features/analysis/AnalysisPage"));
const NetworkPage = lazy(() => import("../features/network/NetworkPage"));

const lazyPage = (node: ReactElement) => <Suspense fallback={<Loading />}>{node}</Suspense>;

export const router = createBrowserRouter([
  {
    path: "/",
    element: <Layout />,
    errorElement: <RouteError />,
    children: [
      { index: true, element: <PlannerPage /> },
      { path: "analyse", element: lazyPage(<AnalysisPage />) },
      { path: "reseau", element: lazyPage(<NetworkPage />) },
      { path: "*", element: <RouteError notFound /> },
    ],
  },
]);
