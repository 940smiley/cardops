import { useMutation, useQueryClient } from "@tanstack/react-query";
import { RefreshCcw, Square } from "lucide-react";
import { api } from "../api";
import type { JobRecord } from "../types";

export function Jobs({ jobs }: { jobs: JobRecord[] }) {
  const queryClient = useQueryClient();
  const cancelMutation = useMutation({
    mutationFn: api.cancelJob,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["jobs"] })
  });
  const retryMutation = useMutation({
    mutationFn: api.retryJob,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["jobs"] })
  });

  return (
    <section className="panel">
      <div className="panel-heading">
        <div>
          <h2>Jobs</h2>
          <p>Durable local queue for scans, processing, exports, and future provider work.</p>
        </div>
      </div>
      <table className="compact-table">
        <thead>
          <tr>
            <th>Job</th>
            <th>Type</th>
            <th>Status</th>
            <th>Attempts</th>
            <th>Result</th>
            <th />
          </tr>
        </thead>
        <tbody>
          {jobs.map((job) => (
            <tr key={job.id}>
              <td>{job.id.slice(0, 8)}</td>
              <td>{job.type}</td>
              <td><span className={`status-chip ${job.status}`}>{job.status}</span></td>
              <td>{job.attempts}/{job.max_attempts}</td>
              <td>{job.error ?? (job.result ? JSON.stringify(job.result) : "—")}</td>
              <td className="row-actions">
                <button
                  className="icon-button"
                  type="button"
                  title="Cancel job"
                  disabled={!["queued", "running"].includes(job.status)}
                  onClick={() => cancelMutation.mutate(job.id)}
                >
                  <Square size={15} />
                </button>
                <button
                  className="icon-button"
                  type="button"
                  title="Retry job"
                  disabled={!["failed", "cancelled"].includes(job.status)}
                  onClick={() => retryMutation.mutate(job.id)}
                >
                  <RefreshCcw size={15} />
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}
