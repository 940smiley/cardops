import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Check, ScanText } from "lucide-react";
import { useEffect, useState } from "react";
import { api } from "../api";
import type { CardIdentification, CardInstance, ImageAsset } from "../types";

const editableFields: Array<keyof CardInstance> = [
  "sport",
  "player",
  "team",
  "manufacturer",
  "brand",
  "set_name",
  "set_year",
  "card_number",
  "parallel",
  "variation",
  "condition_notes"
];

export function IdentificationReview({ images }: { images: ImageAsset[] }) {
  const queryClient = useQueryClient();
  const [selectedImageId, setSelectedImageId] = useState<string>(images[0]?.id ?? "");
  const [result, setResult] = useState<CardIdentification | null>(null);
  const [draft, setDraft] = useState<Partial<CardInstance>>({});

  useEffect(() => {
    if (!selectedImageId && images[0]) setSelectedImageId(images[0].id);
  }, [images, selectedImageId]);

  const identify = useMutation({
    mutationFn: api.identifyImage,
    onSuccess: (data) => {
      setResult(data);
      setDraft({
        ...data.candidate,
        processing_status: "needs_review",
        tags: [...(data.candidate.tags ?? []), "reviewed-before-save"]
      });
    }
  });

  const save = useMutation({
    mutationFn: async () => api.createCardFromImage(selectedImageId, draft),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["cards"] });
      queryClient.invalidateQueries({ queryKey: ["images"] });
    }
  });

  const selectedImage = images.find((image) => image.id === selectedImageId);

  return (
    <div className="two-column">
      <section className="panel">
        <div className="panel-heading">
          <div>
            <h2>Identification Review</h2>
            <p>Analyze one ingested image, review uncertain fields, then save.</p>
          </div>
        </div>
        <div className="stack-form">
          <label className="field">
            <span>Image</span>
            <select value={selectedImageId} onChange={(event) => setSelectedImageId(event.target.value)}>
              {images.map((image) => (
                <option key={image.id} value={image.id}>
                  {image.file_name}
                </option>
              ))}
            </select>
          </label>
          {selectedImage?.thumbnail_path && (
            <img className="review-thumb" src={api.thumbnailUrl(selectedImage.id)} alt={selectedImage.file_name} />
          )}
          <button
            className="primary-button"
            type="button"
            disabled={!selectedImageId || identify.isPending}
            onClick={() => identify.mutate(selectedImageId)}
          >
            <ScanText size={16} />
            Analyze image
          </button>
          {identify.error && <p className="form-error">{String(identify.error.message)}</p>}
        </div>
      </section>

      <section className="panel span-2">
        <div className="panel-heading">
          <div>
            <h2>Candidate Fields</h2>
            <p>Uncertain values remain editable and are saved with manual provenance.</p>
          </div>
          {result && <span className="status-chip">confidence {Math.round(result.confidence * 100)}%</span>}
        </div>
        {!result ? (
          <p className="muted">Choose an image and run analysis.</p>
        ) : (
          <>
            {result.unresolved_fields.length > 0 && (
              <p className="form-error">Unresolved: {result.unresolved_fields.join(", ")}</p>
            )}
            <div className="review-grid">
              {editableFields.map((field) => (
                <label className="field" key={field}>
                  <span>{field.replace(/_/g, " ")}</span>
                  <input
                    value={String(draft[field] ?? "")}
                    onChange={(event) =>
                      setDraft((current) => ({
                        ...current,
                        [field]: field === "set_year" ? Number(event.target.value) || undefined : event.target.value
                      }))
                    }
                  />
                </label>
              ))}
            </div>
            <div className="provider-list">
              {result.evidence.map((item) => (
                <div className="provider-row" key={`${item.field_name}-${item.value}`}>
                  <div>
                    <strong>{item.field_name.replace(/_/g, " ")}</strong>
                    <span>{item.value}</span>
                  </div>
                  <span className="status-chip">{Math.round(item.confidence * 100)}%</span>
                </div>
              ))}
            </div>
            <button className="primary-button" type="button" disabled={save.isPending} onClick={() => save.mutate()}>
              <Check size={16} />
              Save reviewed card
            </button>
            {save.error && <p className="form-error">{String(save.error.message)}</p>}
          </>
        )}
      </section>
    </div>
  );
}
