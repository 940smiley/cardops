import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { FolderOpen, FolderPlus, RefreshCw, RotateCw, Trash2 } from "lucide-react";
import { useMemo, useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { api, formatCapabilityStatus } from "../api";
import type { DirectoryRoot, ImageAsset } from "../types";

const directorySchema = z.object({
  path: z.string().min(2, "Path is required"),
  label: z.string().optional(),
  recursive: z.boolean().default(true)
});

type DirectoryForm = z.infer<typeof directorySchema>;

export function ImageInbox({
  images,
  directories
}: {
  images: ImageAsset[];
  directories: DirectoryRoot[];
}) {
  const queryClient = useQueryClient();
  const [rootToRemove, setRootToRemove] = useState<DirectoryRoot | null>(null);
  const [removeIndexRecords, setRemoveIndexRecords] = useState(false);
  const [actionMessage, setActionMessage] = useState<string | null>(null);
  const form = useForm<DirectoryForm>({
    resolver: zodResolver(directorySchema),
    defaultValues: { recursive: true }
  });

  const invalidateInbox = () => {
    queryClient.invalidateQueries({ queryKey: ["directories"] });
    queryClient.invalidateQueries({ queryKey: ["images"] });
    queryClient.invalidateQueries({ queryKey: ["jobs"] });
  };

  const browse = useMutation({
    mutationFn: api.browseDirectory,
    onSuccess: (result) => {
      if (result.path) {
        form.setValue("path", result.path, { shouldValidate: true, shouldDirty: true });
        setActionMessage("Folder selected.");
      }
    },
    onError: (error) => setActionMessage(error.message)
  });

  const selectAndScan = useMutation({
    mutationFn: async (values: DirectoryForm) => {
      const directory = await api.selectDirectory({
        path: values.path,
        label: values.label,
        recursive: values.recursive,
        exclude_patterns: [],
        allow_symlinks: false
      });
      return api.scanDirectory(directory.id);
    },
    onSuccess: () => {
      invalidateInbox();
      form.reset({ recursive: true });
      setActionMessage("Root registered and scan job started.");
    },
    onError: (error) => setActionMessage(error.message)
  });

  const scan = useMutation({
    mutationFn: api.scanDirectory,
    onSuccess: () => {
      invalidateInbox();
      setActionMessage("Re-index job started.");
    },
    onError: (error) => setActionMessage(error.message)
  });

  const reconnect = useMutation({
    mutationFn: api.reconnectDirectory,
    onSuccess: () => {
      invalidateInbox();
      setActionMessage("Root reconnected.");
    },
    onError: (error) => setActionMessage(error.message)
  });

  const changePath = useMutation({
    mutationFn: ({ directoryId, path }: { directoryId: string; path: string }) =>
      api.updateDirectory(directoryId, { path }),
    onSuccess: () => {
      invalidateInbox();
      setActionMessage("Root path updated.");
    },
    onError: (error) => setActionMessage(error.message)
  });

  const openRoot = useMutation({
    mutationFn: api.openDirectory,
    onSuccess: () => setActionMessage("Root opened in File Explorer."),
    onError: (error) => setActionMessage(error.message)
  });

  const removeRoot = useMutation({
    mutationFn: ({ directoryId, removeRecords }: { directoryId: string; removeRecords: boolean }) =>
      api.removeDirectory(directoryId, {
        confirmed: true,
        remove_index_records: removeRecords
      }),
    onSuccess: () => {
      setRootToRemove(null);
      setRemoveIndexRecords(false);
      invalidateInbox();
      setActionMessage("Root removed from CardOps. Physical files were not deleted.");
    },
    onError: (error) => setActionMessage(error.message)
  });

  const duplicateCount = images.filter((image) => image.duplicate_status === "duplicate").length;
  const invalidRootCount = directories.filter((directory) =>
    ["missing", "invalid", "unavailable", "moved"].includes(directory.status)
  ).length;
  const rootsById = useMemo(
    () => new Map(directories.map((directory) => [directory.id, directory])),
    [directories]
  );

  return (
    <div className="two-column">
      <section className="panel span-2">
        <div className="panel-heading">
          <div>
            <h2>Image Inbox</h2>
            <p>Original files remain in place. CardOps stores metadata and derived thumbnails.</p>
          </div>
          <div className="summary-pair">
            <span>{images.length} images</span>
            <span>{duplicateCount} duplicates</span>
            <span>{invalidRootCount} root warnings</span>
          </div>
        </div>
        {images.length === 0 ? (
          <div className="notice">No indexed images yet. Register a readable local root and scan it.</div>
        ) : (
          <div className="image-grid">
            {images.map((image) => (
              <article className="image-tile" key={image.id}>
                {image.thumbnail_path ? (
                  <img src={api.thumbnailUrl(image.id)} alt={image.file_name} />
                ) : (
                  <div className="thumb-placeholder">No preview</div>
                )}
                <div>
                  <strong>{image.file_name}</strong>
                  <span>{image.relative_path}</span>
                  <span>
                    {image.width ?? "?"} x {image.height ?? "?"}
                  </span>
                  <span>{rootsById.get(image.directory_id)?.label ?? "Inbox root"}</span>
                </div>
                <footer>
                  <span className="status-chip">{image.processing_status}</span>
                  <span className={`status-chip ${image.duplicate_status}`}>{image.duplicate_status}</span>
                  {image.front_back_assignment && <span className="status-chip">{image.front_back_assignment}</span>}
                </footer>
              </article>
            ))}
          </div>
        )}
      </section>

      <section className="panel">
        <div className="panel-heading">
          <div>
            <h2>Register Root</h2>
            <p>Local roots are validated before CardOps can scan them.</p>
          </div>
        </div>
        <form className="stack-form" onSubmit={form.handleSubmit((values) => selectAndScan.mutate(values))}>
          <label className="field">
            <span>Local directory path</span>
            <div className="input-action-row">
              <input placeholder="D:\Cards\Inbox" {...form.register("path")} />
              <button
                className="icon-button"
                type="button"
                title="Browse for a folder"
                disabled={browse.isPending}
                onClick={() => browse.mutate()}
              >
                <FolderOpen size={15} />
              </button>
            </div>
            {form.formState.errors.path && <small>{form.formState.errors.path.message}</small>}
          </label>
          <label className="field">
            <span>Label</span>
            <input placeholder="Raw scan batch" {...form.register("label")} />
          </label>
          <label className="checkbox-row">
            <input type="checkbox" {...form.register("recursive")} />
            <span>Scan subfolders</span>
          </label>
          <button className="primary-button" type="submit" disabled={selectAndScan.isPending}>
            <FolderPlus size={16} />
            Register and scan
          </button>
          {actionMessage && <p className="notice">{actionMessage}</p>}
        </form>
      </section>

      <section className="panel span-2">
        <div className="panel-heading">
          <div>
            <h2>Configured Roots</h2>
            <p>Removing a root never deletes physical files.</p>
          </div>
          <button
            className="secondary-button"
            type="button"
            onClick={() => invalidateInbox()}
          >
            <RefreshCw size={15} />
            Refresh
          </button>
        </div>
        <div className="provider-list">
          {directories.length === 0 && <div className="notice">No Image Inbox roots are configured.</div>}
          {directories.map((directory) => (
            <div className="root-row" key={directory.id}>
              <div className="root-main">
                <div>
                  <strong>{directory.label ?? "Local folder"}</strong>
                  <span>{directory.path}</span>
                  <small>{directory.status_detail}</small>
                </div>
                <span className={`status-chip ${directory.status}`}>{formatCapabilityStatus(directory.status)}</span>
              </div>
              <div className="root-stats">
                <span>{directory.image_count} indexed</span>
                <span>{directory.pending_identification_count} pending ID</span>
                <span>{directory.recursive ? "recursive" : "top folder only"}</span>
              </div>
              <div className="button-row root-actions">
                <button
                  className="secondary-button"
                  type="button"
                  disabled={scan.isPending || directory.status === "revoked"}
                  onClick={() => scan.mutate(directory.id)}
                >
                  <RotateCw size={15} />
                  Re-index
                </button>
                <button
                  className="secondary-button"
                  type="button"
                  disabled={reconnect.isPending}
                  onClick={() => reconnect.mutate(directory.id)}
                >
                  Reconnect
                </button>
                <button
                  className="secondary-button"
                  type="button"
                  onClick={() => {
                    const next = window.prompt("New root path", directory.path);
                    if (next && next !== directory.path) {
                      changePath.mutate({ directoryId: directory.id, path: next });
                    }
                  }}
                >
                  Change path
                </button>
                <button
                  className="secondary-button"
                  type="button"
                  disabled={openRoot.isPending || directory.status !== "active"}
                  onClick={() => openRoot.mutate(directory.id)}
                >
                  <FolderOpen size={15} />
                  Open
                </button>
                <button
                  className="secondary-button danger-button"
                  type="button"
                  title="Remove this root from CardOps without deleting physical files"
                  onClick={() => setRootToRemove(directory)}
                >
                  <Trash2 size={15} />
                  Remove
                </button>
              </div>
            </div>
          ))}
        </div>
      </section>

      {rootToRemove && (
        <section className="panel span-2">
          <div className="panel-heading">
            <div>
              <h2>Remove Root</h2>
              <p>Physical directories and images remain on disk.</p>
            </div>
          </div>
          <div className="removal-summary">
            <span>Root path</span>
            <code>{rootToRemove.path}</code>
            <span>Indexed images</span>
            <strong>{rootToRemove.image_count}</strong>
            <span>Pending identification</span>
            <strong>{rootToRemove.pending_identification_count}</strong>
          </div>
          <label className="checkbox-row">
            <input
              type="checkbox"
              checked={removeIndexRecords}
              onChange={(event) => setRemoveIndexRecords(event.currentTarget.checked)}
            />
            <span>Also remove this root's image records from the CardOps index</span>
          </label>
          <div className="button-row">
            <button className="secondary-button" type="button" onClick={() => setRootToRemove(null)}>
              Cancel
            </button>
            <button
              className="primary-button"
              type="button"
              disabled={removeRoot.isPending}
              onClick={() =>
                removeRoot.mutate({
                  directoryId: rootToRemove.id,
                  removeRecords: removeIndexRecords
                })
              }
            >
              Confirm remove root
            </button>
          </div>
        </section>
      )}
    </div>
  );
}
