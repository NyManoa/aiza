import { Link, NavLink, Outlet } from "react-router";

import { useMeta } from "../api/queries";
import { Icon, type IconName } from "../components/Icon";
import { ThemeToggle } from "../components/ThemeToggle";

const NAV: { to: string; label: string; short: string; icon: IconName; end?: boolean }[] = [
  { to: "/", label: "Itinéraire", short: "Itinéraire", icon: "route", end: true },
  { to: "/analyse", label: "Analyse & couverture", short: "Analyse", icon: "chart" },
  { to: "/reseau", label: "Lignes du réseau", short: "Lignes", icon: "bus" },
];

export function Layout() {
  const meta = useMeta();
  return (
    <>
      <a href="#contenu" className="sr-only">Aller au contenu</a>
      <header className="appbar">
        <div className="appbar-inner">
          <Link to="/" className="brand" aria-label="Accueil — planificateur">
            <span className="brand-logo"><Icon name="bus" /></span>
            <span className="brand-text">
              <strong>Tana Transport</strong>
              <small>Itinéraires par fokontany · Antananarivo</small>
            </span>
          </Link>
          <nav className="topnav" aria-label="Navigation principale">
            {NAV.map((n) => (
              <NavLink key={n.to} to={n.to} end={n.end} className={({ isActive }) => `navlink${isActive ? " active" : ""}`}>
                <Icon name={n.icon} />{n.label}
              </NavLink>
            ))}
          </nav>
          <ThemeToggle />
        </div>
      </header>
      <main className="page" id="contenu">
        <Outlet />
      </main>
      <footer className="foot">
        Sources : <code>mdg_admin_boundaries.xlsx</code> (OCHA/HDX 2018) et <code>liste_bus_antananarivo.txt</code>.
        Règles déterministes, sans IA. Distances à vol d'oiseau ; sens retour des lignes non circulaires supposé ;
        liaisons suburbaines sans arrêts intermédiaires connus.{meta.data && <> · v{meta.data.version}</>}
      </footer>
      <nav className="bottomnav" aria-label="Navigation">
        {NAV.map((n) => (
          <NavLink key={n.to} to={n.to} end={n.end} className={({ isActive }) => (isActive ? "active" : "")}>
            <Icon name={n.icon} /><span>{n.short}</span>
          </NavLink>
        ))}
        <ThemeToggle variant="tab" />
      </nav>
    </>
  );
}
