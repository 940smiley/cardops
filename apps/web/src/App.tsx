import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Boxes, BriefcaseBusiness, ClipboardList, Images, LayoutDashboard, Settings, Tags } from "lucide-react";
import { api } from "./api";
import { Dashboard } from "./components/Dashboard";
import { EbayConnection } from "./components/EbayConnection";
import { ExportsPanel } from "./components/ExportsPanel";
import { IdentificationReview } from "./components/IdentificationReview";
import { ImageInbox } from "./components/ImageInbox";
import { Inventory } from "./components/Inventory";
import { Jobs } from "./components/Jobs";
import { SettingsPanel } from "./components/SettingsPanel";
import { Sidebar } from "./components/Sidebar";

const navItems = [
  { id: "dashboard", label: "Dashboard", icon: LayoutDashboard, enabled: true },
  { id: "inventory", label: "Inventory", icon: Boxes, enabled: true },
  { id: "image-inbox", label: "Image Inbox", icon: Images, enabled: true },
  { id: "identification-review", label: "Identification Review", icon: ClipboardList, enabled: true },
  { id: "listings", label: "Listings", icon: BriefcaseBusiness, enabled: false },
  { id: "listing-audits", label: "Listing Audits", icon: ClipboardList, enabled: false },
  { id: "lot-builder", label: "Lot Builder", icon: Tags, enabled: false },
  { id: "pricing", label: "Pricing", icon: Tags, enabled: false },
  { id: "draft-queue", label: "Draft Queue", icon: ClipboardList, enabled: false },
  { id: "ebay-connection", label: "eBay Connection", icon: BriefcaseBusiness, enabled: true },
  { id: "imports-exports", label: "Imports and Exports", icon: ClipboardList, enabled: true },
  { id: "jobs", label: "Jobs", icon: ClipboardList, enabled: true },
  { id: "settings", label: "Settings", icon: Settings, enabled: true },
  { id: "audit-log", label: "Audit Log", icon: ClipboardList, enabled: false }
] as const;

export type AppSection = (typeof navItems)[number]["id"];

export function App() {
  const [section, setSection] = useState<AppSection>("dashboard");
  const health = useQuery({ queryKey: ["health"], queryFn: api.health });
  const capabilities = useQuery({ queryKey: ["capabilities"], queryFn: api.capabilities });
  const cards = useQuery({ queryKey: ["cards"], queryFn: api.cards });
  const images = useQuery({ queryKey: ["images"], queryFn: api.images });
  const directories = useQuery({ queryKey: ["directories"], queryFn: api.directories });
  const jobs = useQuery({ queryKey: ["jobs"], queryFn: api.jobs, refetchInterval: 3000 });

  const commonProps = {
    cards: cards.data ?? [],
    images: images.data ?? [],
    jobs: jobs.data ?? [],
    directories: directories.data ?? [],
    capabilities: capabilities.data
  };

  return (
    <div className="app-shell">
      <Sidebar items={navItems} current={section} onSelect={setSection} />
      <main className="workspace">
        <header className="topbar">
          <div>
            <h1>CardOps AI</h1>
            <p>Local inventory, image intake, and listing operations</p>
          </div>
          <div className="runtime-status" aria-label="Runtime status">
            <span className={health.data?.status === "ok" ? "dot ok" : "dot warn"} />
            <span>API {health.data?.status ?? "checking"}</span>
            <span>Demo {health.data?.demo_mode ? "on" : "off"}</span>
          </div>
        </header>

        {section === "dashboard" && <Dashboard {...commonProps} />}
        {section === "inventory" && <Inventory cards={commonProps.cards} />}
        {section === "image-inbox" && (
          <ImageInbox
            images={commonProps.images}
            directories={commonProps.directories}
          />
        )}
        {section === "identification-review" && <IdentificationReview images={commonProps.images} />}
        {section === "imports-exports" && <ExportsPanel />}
        {section === "ebay-connection" && <EbayConnection />}
        {section === "jobs" && <Jobs jobs={commonProps.jobs} />}
        {section === "settings" && <SettingsPanel capabilities={commonProps.capabilities} />}
        {!navItems.find((item) => item.id === section)?.enabled && (
          <section className="panel">
            <h2>{navItems.find((item) => item.id === section)?.label}</h2>
            <p className="muted">
              This section is intentionally marked planned until its backend workflow is implemented in
              the next phases.
            </p>
          </section>
        )}
      </main>
    </div>
  );
}
