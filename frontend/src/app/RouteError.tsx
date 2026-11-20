import { isRouteErrorResponse, Link, useRouteError } from "react-router";

export function RouteError({ notFound = false }: { notFound?: boolean }) {
  const err = useRouteError();
  const title = notFound || (isRouteErrorResponse(err) && err.status === 404) ? "Page introuvable" : "Erreur inattendue";
  return (
    <main>
      <div className="card">
        <h2>{title}</h2>
        {!notFound && err instanceof Error && <p className="muted">{err.message}</p>}
        <p><Link to="/">Retour au planificateur</Link></p>
      </div>
    </main>
  );
}
