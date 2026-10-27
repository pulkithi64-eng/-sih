import { useEffect, useMemo, useState } from "react";
import { ArrowDown, ArrowUp, Braces, Loader2, Lock, Plus, Save, Search, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Textarea } from "@/components/ui/textarea";
import { EmptyState, ErrorState } from "@/components/common/EmptyState";
import { PageHeader } from "@/components/common/PageHeader";
import { SeverityBadge } from "@/components/common/SeverityBadge";
import { useChecklists, useMeta, useRules, useUpdateChecklist, useUpdateRule } from "@/lib/hooks";
import { CATEGORY_LABEL, CATEGORY_SHORT, humanize } from "@/lib/labels";
import type { ChecklistItem, Rule, Severity } from "@/lib/types";
import { cn } from "@/lib/utils";
import { isAdmin, useAuth } from "../auth";
import { Panel } from "../components/Panel";
import { TableSkeleton } from "../components/Skeletons";

const SEVERITIES: Severity[] = ["CRITICAL", "MAJOR", "MINOR", "INFO"];

export default function RulesPage() {
  const { user } = useAuth();
  const admin = isAdmin(user?.role);
  return (
    <div>
      <PageHeader
        title="Rules & checklists"
        description="Configurable validation rules and category checklists. Clause references are illustrative and versioned; every change is audited."
        actions={
          !admin && (
            <span className="inline-flex items-center gap-1.5 rounded-md border bg-card px-2.5 py-1 text-xs text-muted-foreground">
              <Lock className="h-3.5 w-3.5" /> Read-only · editable by administrators
            </span>
          )
        }
      />
      <Tabs defaultValue="rules">
        <TabsList>
          <TabsTrigger value="rules">Rules</TabsTrigger>
          <TabsTrigger value="checklists">Checklists</TabsTrigger>
        </TabsList>
        <TabsContent value="rules" className="mt-4">
          <RulesTable admin={admin} />
        </TabsContent>
        <TabsContent value="checklists" className="mt-4">
          <ChecklistEditor admin={admin} />
        </TabsContent>
      </Tabs>
    </div>
  );
}

function RulesTable({ admin }: { admin: boolean }) {
  const q = useRules();
  const upd = useUpdateRule();
  const [search, setSearch] = useState("");
  const [type, setType] = useState("ALL");
  const [editing, setEditing] = useState<Rule | null>(null);
  const rules = q.data ?? [];
  const types = [...new Set(rules.map((r) => r.type))].sort();
  const shown = rules.filter(
    (r) =>
      (type === "ALL" || r.type === type) &&
      (!search || `${r.id} ${r.name} ${r.description} ${r.clause}`.toLowerCase().includes(search.toLowerCase())),
  );
  const enabled = rules.filter((r) => r.enabled).length;

  return (
    <div className="card-surface">
      <div className="flex flex-wrap items-center gap-2 border-b p-3">
        <div className="relative min-w-[200px] flex-1">
          <Search className="pointer-events-none absolute left-2.5 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <Input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Search rules, clauses" className="h-9 pl-8" aria-label="Search rules" />
        </div>
        <Select value={type} onValueChange={setType}>
          <SelectTrigger className="h-9 w-auto min-w-[200px]" aria-label="Rule type">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="ALL">All rule types</SelectItem>
            {types.map((t) => (
              <SelectItem key={t} value={t}>
                {humanize(t)}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <span className="ml-auto text-xs text-muted-foreground">
          {enabled} of {rules.length} enabled
        </span>
      </div>
      {q.isLoading ? (
        <TableSkeleton rows={8} cols={6} />
      ) : q.isError ? (
        <ErrorState error={q.error} onRetry={() => q.refetch()} />
      ) : shown.length === 0 ? (
        <EmptyState title="No rules match" />
      ) : (
        <Table>
          <TableHeader>
            <TableRow className="hover:bg-transparent">
              <TableHead className="w-16">Enabled</TableHead>
              <TableHead>Rule</TableHead>
              <TableHead className="hidden lg:table-cell">Type</TableHead>
              <TableHead>Severity</TableHead>
              <TableHead className="hidden xl:table-cell">Clause (illustrative)</TableHead>
              <TableHead className="hidden md:table-cell">Params</TableHead>
              <TableHead className="w-14 text-right">Ver.</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {shown.map((r) => (
              <TableRow key={r.id} className={cn(!r.enabled && "bg-slate-50/60 text-muted-foreground")}>
                <TableCell>
                  <Switch
                    checked={r.enabled}
                    disabled={!admin || upd.isPending}
                    onCheckedChange={(v) => upd.mutate({ id: r.id, body: { enabled: v } })}
                    aria-label={`${r.enabled ? "Disable" : "Enable"} ${r.name}`}
                  />
                </TableCell>
                <TableCell className="max-w-[360px]">
                  <p className="font-medium text-foreground">{r.name}</p>
                  <p className="mono text-2xs text-muted-foreground">{r.id}</p>
                  <p className="mt-0.5 line-clamp-2 text-xs text-muted-foreground">{r.description}</p>
                  <p className="mt-1 flex flex-wrap gap-1">
                    {(r.categories ?? []).map((c) => (
                      <span key={c} className="rounded bg-muted px-1 text-2xs text-muted-foreground">
                        {CATEGORY_SHORT[c as keyof typeof CATEGORY_SHORT] ?? humanize(c)}
                      </span>
                    ))}
                  </p>
                </TableCell>
                <TableCell className="hidden text-xs lg:table-cell">{humanize(r.type)}</TableCell>
                <TableCell>
                  {admin ? (
                    <Select value={r.severity} onValueChange={(v) => upd.mutate({ id: r.id, body: { severity: v } })}>
                      <SelectTrigger className="h-8 w-[112px] text-xs" aria-label={`Severity for ${r.name}`}>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        {SEVERITIES.map((s) => (
                          <SelectItem key={s} value={s}>
                            {humanize(s)}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  ) : (
                    <SeverityBadge severity={r.severity} />
                  )}
                </TableCell>
                <TableCell className="hidden max-w-[220px] text-xs xl:table-cell">{r.clause}</TableCell>
                <TableCell className="hidden md:table-cell">
                  <button
                    type="button"
                    onClick={() => setEditing(r)}
                    className="mono block max-w-[220px] truncate rounded border bg-slate-50 px-1.5 py-0.5 text-left text-2xs hover:border-primary-600/50"
                    title={admin ? "Edit parameters" : "View parameters"}
                  >
                    {JSON.stringify(r.params ?? {})}
                  </button>
                </TableCell>
                <TableCell className="tabular text-right text-xs">v{String(r.version)}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      )}
      <ParamsDialog rule={editing} admin={admin} onClose={() => setEditing(null)} />
    </div>
  );
}

function ParamsDialog({ rule, admin, onClose }: { rule: Rule | null; admin: boolean; onClose: () => void }) {
  const upd = useUpdateRule();
  const [text, setText] = useState("");
  useEffect(() => {
    if (rule) setText(JSON.stringify(rule.params ?? {}, null, 2));
  }, [rule]);
  const parsed = useMemo(() => {
    try {
      const v = JSON.parse(text || "{}");
      if (typeof v !== "object" || Array.isArray(v) || v === null) return { error: "Parameters must be a JSON object." };
      return { value: v as Record<string, unknown> };
    } catch (e) {
      return { error: (e as Error).message };
    }
  }, [text]);
  return (
    <Dialog open={!!rule} onOpenChange={(o) => !o && onClose()}>
      <DialogContent className="sm:max-w-xl">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Braces className="h-4 w-4" /> {rule?.name}
          </DialogTitle>
          <DialogDescription>
            <span className="mono">{rule?.id}</span> · {humanize(rule?.type)} · v{String(rule?.version ?? "")}
          </DialogDescription>
        </DialogHeader>
        <Textarea
          value={text}
          onChange={(e) => setText(e.target.value)}
          readOnly={!admin}
          rows={12}
          spellCheck={false}
          className={cn("mono text-xs", parsed.error && "border-red-500 focus-visible:ring-red-500")}
          aria-label="Rule parameters JSON"
          aria-invalid={!!parsed.error}
        />
        {parsed.error ? <p className="text-xs text-red-700">Invalid JSON: {parsed.error}</p> : <p className="text-xs text-muted-foreground">Valid JSON. Saving bumps the ruleset version.</p>}
        <DialogFooter>
          <Button variant="outline" onClick={onClose}>
            {admin ? "Cancel" : "Close"}
          </Button>
          {admin && (
            <Button
              disabled={!!parsed.error || upd.isPending}
              onClick={() => rule && parsed.value && upd.mutate({ id: rule.id, body: { params: parsed.value } }, { onSuccess: onClose })}
            >
              {upd.isPending ? <Loader2 className="mr-1.5 h-4 w-4 animate-spin" /> : <Save className="mr-1.5 h-4 w-4" />}
              Save parameters
            </Button>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function normalise(raw: any): Record<string, ChecklistItem[]> {
  const out: Record<string, ChecklistItem[]> = {};
  if (!raw || typeof raw !== "object") return out;
  const src = raw.categories && typeof raw.categories === "object" ? raw.categories : raw;
  for (const [k, v] of Object.entries<any>(src)) {
    if (Array.isArray(v)) out[k] = v;
    else if (v && Array.isArray(v.items)) out[k] = v.items;
  }
  return out;
}

function ChecklistEditor({ admin }: { admin: boolean }) {
  const q = useChecklists();
  const meta = useMeta();
  const save = useUpdateChecklist();
  const all = normalise(q.data);
  const cats = Object.keys(all).length ? Object.keys(all) : Object.keys(CATEGORY_LABEL);
  const [cat, setCat] = useState<string>("EOA");
  const [items, setItems] = useState<ChecklistItem[]>([]);
  const [dirty, setDirty] = useState(false);
  useEffect(() => {
    setItems((all[cat] ?? []).map((x) => ({ ...x })));
    setDirty(false);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [cat, q.data]);
  const docTypes = meta.data?.docTypes ?? [];
  const label = (id: string) => docTypes.find((d) => d.id === id)?.label ?? humanize(id);
  const update = (i: number, patch: Partial<ChecklistItem>) => {
    setItems((xs) => xs.map((x, j) => (i === j ? { ...x, ...patch } : x)));
    setDirty(true);
  };
  const move = (i: number, d: number) => {
    setItems((xs) => {
      const n = [...xs];
      const [x] = n.splice(i, 1);
      n.splice(i + d, 0, x);
      return n;
    });
    setDirty(true);
  };

  if (q.isLoading) return <TableSkeleton rows={8} cols={4} />;
  if (q.isError) return <ErrorState error={q.error} onRetry={() => q.refetch()} />;

  return (
    <Panel
      title={
        <span className="flex items-center gap-3">
          Checklist for
          <Select value={cat} onValueChange={setCat}>
            <SelectTrigger className="h-8 w-auto min-w-[220px]" aria-label="Category">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {cats.map((c) => (
                <SelectItem key={c} value={c}>
                  {CATEGORY_LABEL[c as keyof typeof CATEGORY_LABEL] ?? humanize(c)}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </span>
      }
      actions={
        admin && (
          <>
            <Button
              size="sm"
              variant="outline"
              onClick={() => {
                setItems((xs) => [...xs, { docType: "OTHER", label: "", mandatory: false, clause: "" }]);
                setDirty(true);
              }}
            >
              <Plus className="mr-1 h-4 w-4" /> Add item
            </Button>
            <Button size="sm" disabled={!dirty || save.isPending} onClick={() => save.mutate({ category: cat, items }, { onSuccess: () => setDirty(false) })}>
              {save.isPending ? <Loader2 className="mr-1.5 h-4 w-4 animate-spin" /> : <Save className="mr-1.5 h-4 w-4" />}
              Save checklist
            </Button>
          </>
        )
      }
      flush
    >
      {items.length === 0 ? (
        <EmptyState compact title="No items in this checklist" />
      ) : (
        <Table>
          <TableHeader>
            <TableRow className="hover:bg-transparent">
              <TableHead className="w-10">#</TableHead>
              <TableHead>Document type</TableHead>
              <TableHead className="w-28">Mandatory</TableHead>
              <TableHead>Clause (illustrative)</TableHead>
              {admin && <TableHead className="w-28"><span className="sr-only">Actions</span></TableHead>}
            </TableRow>
          </TableHeader>
          <TableBody>
            {items.map((it: any, i) => (
              <TableRow key={`${it.docType}-${i}`}>
                <TableCell className="tabular text-xs text-muted-foreground">{i + 1}</TableCell>
                <TableCell className="min-w-[220px]">
                  {admin ? (
                    <Select value={it.docType} onValueChange={(v) => update(i, { docType: v, label: label(v) })}>
                      <SelectTrigger className="h-8 text-sm" aria-label="Document type">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        {(docTypes.length ? docTypes : [{ id: it.docType, label: label(it.docType) }]).map((d) => (
                          <SelectItem key={d.id} value={d.id}>
                            {d.label}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  ) : (
                    <span className="font-medium">{it.label || label(it.docType)}</span>
                  )}
                  {it.when && (
                    <p className="mono mt-1 text-2xs text-blue-800">
                      Conditional: {String(it.when.field ?? "").replace("formData.", "")} {Object.keys(it.when).filter((k) => k !== "field").join(" ")}
                    </p>
                  )}
                </TableCell>
                <TableCell>
                  <Switch checked={!!it.mandatory} disabled={!admin} onCheckedChange={(v) => update(i, { mandatory: v })} aria-label="Mandatory" />
                </TableCell>
                <TableCell className="min-w-[240px]">
                  {admin ? (
                    <Input value={it.clause ?? ""} onChange={(e) => update(i, { clause: e.target.value })} className="h-8 text-xs" aria-label="Clause" />
                  ) : (
                    <span className="text-xs text-muted-foreground">{it.clause}</span>
                  )}
                </TableCell>
                {admin && (
                  <TableCell>
                    <div className="flex justify-end gap-0.5">
                      <Button variant="ghost" size="icon" className="h-7 w-7" disabled={i === 0} onClick={() => move(i, -1)} aria-label="Move up">
                        <ArrowUp className="h-3.5 w-3.5" />
                      </Button>
                      <Button variant="ghost" size="icon" className="h-7 w-7" disabled={i === items.length - 1} onClick={() => move(i, 1)} aria-label="Move down">
                        <ArrowDown className="h-3.5 w-3.5" />
                      </Button>
                      <Button
                        variant="ghost"
                        size="icon"
                        className="h-7 w-7"
                        onClick={() => {
                          setItems((xs) => xs.filter((_, j) => j !== i));
                          setDirty(true);
                        }}
                        aria-label="Remove item"
                      >
                        <Trash2 className="h-3.5 w-3.5" />
                      </Button>
                    </div>
                  </TableCell>
                )}
              </TableRow>
            ))}
          </TableBody>
        </Table>
      )}
    </Panel>
  );
}
