import { zodResolver } from "@hookform/resolvers/zod";
import {
  createColumnHelper,
  flexRender,
  getCoreRowModel,
  getFilteredRowModel,
  useReactTable
} from "@tanstack/react-table";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Plus, Search } from "lucide-react";
import { useMemo, useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { api } from "../api";
import type { CardInstance } from "../types";

const cardSchema = z.object({
  sport: z.string().optional(),
  player: z.string().min(1, "Player or subject is required"),
  team: z.string().optional(),
  manufacturer: z.string().optional(),
  brand: z.string().optional(),
  set_name: z.string().optional(),
  set_year: z.coerce.number().int().min(1800).max(2200).optional(),
  card_number: z.string().optional(),
  estimated_value: z.coerce.number().min(0).optional(),
  storage_location: z.string().optional()
});

type CardForm = z.infer<typeof cardSchema>;

const columnHelper = createColumnHelper<CardInstance>();

export function Inventory({ cards }: { cards: CardInstance[] }) {
  const [globalFilter, setGlobalFilter] = useState("");
  const queryClient = useQueryClient();
  const createMutation = useMutation({
    mutationFn: api.createCard,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["cards"] })
  });
  const approveMutation = useMutation({
    mutationFn: api.approveCard,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["cards"] })
  });

  const columns = useMemo(
    () => [
      columnHelper.accessor("internal_sku", { header: "SKU" }),
      columnHelper.accessor("sport", { header: "Sport", cell: (info) => info.getValue() ?? "—" }),
      columnHelper.accessor("player", { header: "Player", cell: (info) => info.getValue() ?? "Unknown" }),
      columnHelper.accessor("team", { header: "Team", cell: (info) => info.getValue() ?? "—" }),
      columnHelper.accessor("set_year", { header: "Year", cell: (info) => info.getValue() ?? "—" }),
      columnHelper.accessor("set_name", { header: "Set", cell: (info) => info.getValue() ?? "—" }),
      columnHelper.accessor("card_number", { header: "No.", cell: (info) => info.getValue() ?? "—" }),
      columnHelper.accessor("estimated_value", {
        header: "Est.",
        cell: (info) => `$${Number(info.getValue() ?? 0).toFixed(2)}`
      }),
      columnHelper.accessor("processing_status", {
        header: "Status",
        cell: (info) => <span className="status-chip">{info.getValue()}</span>
      }),
      columnHelper.display({
        id: "actions",
        header: "",
        cell: (info) => (
          <button
            type="button"
            className="inline-button"
            onClick={() => approveMutation.mutate(info.row.original.id)}
            disabled={info.row.original.processing_status === "approved"}
          >
            Approve
          </button>
        )
      })
    ],
    [approveMutation]
  );

  const table = useReactTable({
    data: cards,
    columns,
    state: { globalFilter },
    onGlobalFilterChange: setGlobalFilter,
    getCoreRowModel: getCoreRowModel(),
    getFilteredRowModel: getFilteredRowModel()
  });

  const form = useForm<CardForm>({ resolver: zodResolver(cardSchema) });

  return (
    <div className="two-column">
      <section className="panel span-2">
        <div className="panel-heading">
          <div>
            <h2>Inventory</h2>
            <p>Stable internal SKUs are separate from marketplace listing IDs.</p>
          </div>
          <label className="search-box">
            <Search size={15} />
            <input
              value={globalFilter}
              onChange={(event) => setGlobalFilter(event.target.value)}
              placeholder="Filter inventory"
            />
          </label>
        </div>
        <div className="table-scroll">
          <table className="compact-table">
            <thead>
              {table.getHeaderGroups().map((group) => (
                <tr key={group.id}>
                  {group.headers.map((header) => (
                    <th key={header.id}>
                      {flexRender(header.column.columnDef.header, header.getContext())}
                    </th>
                  ))}
                </tr>
              ))}
            </thead>
            <tbody>
              {table.getRowModel().rows.map((row) => (
                <tr key={row.id}>
                  {row.getVisibleCells().map((cell) => (
                    <td key={cell.id}>{flexRender(cell.column.columnDef.cell, cell.getContext())}</td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section className="panel">
        <div className="panel-heading">
          <div>
            <h2>Add Card</h2>
            <p>Manual values are stored with provenance.</p>
          </div>
        </div>
        <form
          className="stack-form"
          onSubmit={form.handleSubmit((values) =>
            createMutation.mutate(
              {
                ...values,
                processing_status: "manual",
                confidence: 1,
                quantity: 1,
                raw_or_graded: "raw",
                tags: ["manual"]
              },
              { onSuccess: () => form.reset() }
            )
          )}
        >
          <Field label="Player" {...form.register("player")} error={form.formState.errors.player?.message} />
          <Field label="Sport" {...form.register("sport")} />
          <Field label="Team" {...form.register("team")} />
          <Field label="Manufacturer" {...form.register("manufacturer")} />
          <Field label="Brand" {...form.register("brand")} />
          <Field label="Set" {...form.register("set_name")} />
          <Field label="Year" type="number" {...form.register("set_year")} />
          <Field label="Card number" {...form.register("card_number")} />
          <Field label="Estimated value" type="number" step="0.01" {...form.register("estimated_value")} />
          <Field label="Storage location" {...form.register("storage_location")} />
          <button className="primary-button" type="submit" disabled={createMutation.isPending}>
            <Plus size={16} />
            Add card
          </button>
        </form>
      </section>
    </div>
  );
}

interface FieldProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label: string;
  error?: string;
}

function Field({ label, error, ...inputProps }: FieldProps) {
  return (
    <label className="field">
      <span>{label}</span>
      <input {...inputProps} />
      {error && <small>{error}</small>}
    </label>
  );
}
