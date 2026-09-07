import { Outlet, NavLink } from "react-router-dom";
import clsx from "clsx";

export function Layout() {
  return (
    <div className="flex flex-col h-screen overflow-hidden relative" style={{ backgroundColor: 'var(--color-surface)', color: 'var(--color-on-surface)' }}>
      {/* Dark HUD overlay */}
      <div className="absolute inset-0 pointer-events-none shadow-[inset_0_0_100px_rgba(0,0,0,0.8)] z-50"></div>
      
      <div className="flex flex-1 h-full z-10 relative">
        <aside className="w-64 border-r border-outline-variant flex flex-col p-6 shrink-0 bg-surface">
          <div className="font-display-lg text-[32px] text-primary tracking-tighter mb-12">LUMEN</div>
          
          <nav className="flex flex-col gap-2">
            <NavItem to="/mapping" label="01. Mapping/Geometry" />
            <NavItem to="/pipeline" label="02. Pipeline" />
            <NavItem to="/evaluation" label="03. Evaluation" />
            <NavItem to="/datasets" label="04. Datasets" />
          </nav>
        </aside>

        <main className="flex-1 overflow-hidden">
          <Outlet />
        </main>
      </div>
    </div>
  );
}

function NavItem({ to, label }) {
  return (
    <NavLink 
      to={to} 
      className={({isActive}) => clsx(
        "font-telemetry-data text-[11px] font-bold uppercase py-3 border-b border-dashed border-outline-variant cursor-pointer transition-colors",
        isActive ? "text-primary" : "text-on-surface hover:text-primary"
      )}
    >
      {label}
    </NavLink>
  );
}
