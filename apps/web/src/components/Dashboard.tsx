import { formatCount } from "@cardops/shared";
import { api, formatCapabilityStatus } from "../api";
import type { CardInstance, DirectoryRoot, ImageAsset, JobRecord, SystemCapabilities } from "../types";

interface DashboardProps {
  cards: CardInstance[];
  images: ImageAsset[];
  jobs: JobRecord[];
  directories: DirectoryRoot[];
  capabilities?: SystemCapabilities;
}

export function Dashboard({ cards, images, jobs, directories, capabilities }: DashboardProps) {
  const identified = cards.filter((card) => card.processing_status === "approved").length;
  const needingReview = cards.filter((card) => card.processing_status !== "approved").length;
  const duplicates = images.filter((image) => image.duplicate_status === "duplicate").length;
  const failedJobs = jobs.filter((job) => job.status === "failed").length;
  const missingBack = images.filter((image) => image.front_back_assignment !== "back").length;
  const unlistedValue = cards.reduce((sum, card) => sum + (Number(card.estimated_value) || 0), 0);

  return (
    <div className="dashboard-grid">
      <section className="metric-strip" aria-label="Inventory summary">
        <Metric label="Total card instances" value={formatCount(cards.length)} />
        <Metric label="Identified cards" value={formatCount(identified)} />
        <Metric label="Needs review" value={formatCount(needingReview)} tone="amber" />
        <Metric label="Missing back images" value={formatCount(missingBack)} tone="amber" />
        <Metric label="Duplicates" value={formatCount(duplicates)} tone={duplicates ? "amber" : "teal"} />
        <Metric label="Failed jobs" value={formatCount(failedJobs)} tone={failedJobs ? "red" : "teal"} />
        <Metric label="Unlisted est. value" value={`$${unlistedValue.toFixed(2)}`} />
      </section>

      <section className="panel span-2">
        <div className="panel-heading">
          <div>
            <h2>Recent Inventory</h2>
            <p>Manual entries and demo fixtures use the same card service.</p>
          </div>
        </div>
        <table className="compact-table">
          <thead>
            <tr>
              <th>SKU</th>
              <th>Player</th>
              <th>Set</th>
              <th>Year</th>
              <th>Status</th>
              <th>Value</th>
            </tr>
          </thead>
          <tbody>
            {cards.slice(0, 7).map((card) => (
              <tr key={card.id}>
                <td>{card.internal_sku}</td>
                <td>{card.player ?? "Unknown"}</td>
                <td>{card.set_name ?? "Unspecified"}</td>
                <td>{card.set_year ?? "—"}</td>
                <td><span className="status-chip">{card.processing_status}</span></td>
                <td>${Number(card.estimated_value ?? 0).toFixed(2)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      <section className="panel">
        <div className="panel-heading">
          <div>
            <h2>Provider Capabilities</h2>
            <p>Unavailable providers do not block local workflows.</p>
          </div>
        </div>
        <div className="provider-list">
          {capabilities?.providers.map((provider) => (
            <div className="provider-row" key={provider.name}>
              <div>
                <strong>{provider.name}</strong>
                <span>{provider.capabilities[0] ?? provider.limitations[0] ?? "No active capability"}</span>
              </div>
              <span className={`status-chip ${provider.status}`}>{formatCapabilityStatus(provider.status)}</span>
            </div>
          ))}
        </div>
      </section>

      <section className="panel">
        <div className="panel-heading">
          <div>
            <h2>Image Inbox</h2>
            <p>{directories.length} registered root{directories.length === 1 ? "" : "s"}</p>
          </div>
        </div>
        <div className="thumbnail-strip">
          {images.slice(0, 6).map((image) => (
            <figure key={image.id}>
              {image.thumbnail_path ? (
                <img src={api.thumbnailUrl(image.id)} alt={image.file_name} />
              ) : (
                <div className="thumb-placeholder">No preview</div>
              )}
              <figcaption>{image.front_back_assignment ?? image.duplicate_status}</figcaption>
            </figure>
          ))}
        </div>
      </section>

      <section className="panel">
        <div className="panel-heading">
          <div>
            <h2>Recent Jobs</h2>
            <p>Database-backed queue for scans and future processors.</p>
          </div>
        </div>
        <div className="job-list">
          {jobs.slice(0, 5).map((job) => (
            <div className="job-row" key={job.id}>
              <div>
                <strong>{job.type}</strong>
                <span>{job.id.slice(0, 8)}</span>
              </div>
              <span className={`status-chip ${job.status}`}>{job.status}</span>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}

function Metric({ label, value, tone = "teal" }: { label: string; value: string; tone?: string }) {
  return (
    <div className={`metric ${tone}`}>
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}
