import type { LucideIcon } from "lucide-react";
import type { AppSection } from "../App";

interface SidebarItem {
  id: AppSection;
  label: string;
  icon: LucideIcon;
  enabled: boolean;
}

interface SidebarProps {
  items: readonly SidebarItem[];
  current: AppSection;
  onSelect: (section: AppSection) => void;
}

export function Sidebar({ items, current, onSelect }: SidebarProps) {
  return (
    <aside className="sidebar">
      <div className="brand">
        <div className="brand-mark">CO</div>
        <div>
          <strong>CardOps AI</strong>
          <span>Local-first</span>
        </div>
      </div>
      <nav aria-label="Primary">
        {items.map((item) => {
          const Icon = item.icon;
          return (
            <button
              key={item.id}
              className={`nav-item ${current === item.id ? "active" : ""}`}
              type="button"
              disabled={!item.enabled}
              onClick={() => onSelect(item.id)}
              title={item.enabled ? item.label : `${item.label} is planned`}
            >
              <Icon size={16} aria-hidden="true" />
              <span>{item.label}</span>
              {!item.enabled && <small>planned</small>}
            </button>
          );
        })}
      </nav>
    </aside>
  );
}
