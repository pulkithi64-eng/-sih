import { Plus, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import type { ApplicationCategory } from "@/lib/types";
import { Panel } from "../../components/Panel";

export interface Programme {
  level: string;
  programme: string;
  course: string;
  shift: string;
  intake: number | "";
}

export interface FormState {
  programmes: Programme[];
  proposedIntake: number | "";
  facultyCount: number | "";
  studentCount: number | "";
  landAreaAcres: number | "";
  builtUpAreaSqm: number | "";
  locationType: string;
  terTxnId: string;
  nbaAccredited: boolean;
  naacAccredited: boolean;
  cadre: { professor: number | ""; associateProfessor: number | ""; assistantProfessor: number | "" };
  [k: string]: any;
}

export const EMPTY_FORM: FormState = {
  programmes: [{ level: "UG", programme: "Engineering & Technology", course: "", shift: "1", intake: "" }],
  proposedIntake: "",
  facultyCount: "",
  studentCount: "",
  landAreaAcres: "",
  builtUpAreaSqm: "",
  locationType: "URBAN",
  terTxnId: "",
  nbaAccredited: false,
  naacAccredited: false,
  cadre: { professor: "", associateProfessor: "", assistantProfessor: "" },
};

export function formFromData(d: Record<string, any> | undefined): FormState {
  if (!d) return EMPTY_FORM;
  return {
    ...EMPTY_FORM,
    ...d,
    programmes: Array.isArray(d.programmes) && d.programmes.length ? d.programmes : EMPTY_FORM.programmes,
    cadre: { ...EMPTY_FORM.cadre, ...(d.cadre ?? {}) },
    nbaAccredited: d.nbaAccredited === true || d.nbaAccredited === "true",
    naacAccredited: d.naacAccredited === true || d.naacAccredited === "true",
  };
}

const n = (v: any) => (v === "" || v === null || v === undefined ? undefined : Number(v));

export function formToData(f: FormState): Record<string, unknown> {
  const programmes = f.programmes
    .filter((p) => p.course.trim())
    .map((p) => ({ ...p, intake: n(p.intake) ?? 0 }));
  const totalIntake = programmes.reduce((s, p) => s + (Number(p.intake) || 0), 0);
  const cadre = {
    professor: n(f.cadre.professor),
    associateProfessor: n(f.cadre.associateProfessor),
    assistantProfessor: n(f.cadre.assistantProfessor),
  };
  const out: Record<string, unknown> = {
    ...Object.fromEntries(Object.entries(f).filter(([k]) => !(k in EMPTY_FORM))),
    programmes,
    totalIntake: totalIntake || undefined,
    proposedIntake: n(f.proposedIntake),
    facultyCount: n(f.facultyCount),
    studentCount: n(f.studentCount),
    landAreaAcres: n(f.landAreaAcres),
    builtUpAreaSqm: n(f.builtUpAreaSqm),
    locationType: f.locationType || undefined,
    terTxnId: f.terTxnId.trim() || undefined,
    nbaAccredited: f.nbaAccredited,
    naacAccredited: f.naacAccredited,
    cadre: Object.values(cadre).some((x) => x !== undefined) ? cadre : undefined,
  };
  Object.keys(out).forEach((k) => out[k] === undefined && delete out[k]);
  return out;
}

function NumField({ id, label, value, onChange, hint, step }: { id: string; label: string; value: number | ""; onChange: (v: number | "") => void; hint?: string; step?: string }) {
  return (
    <div className="space-y-1.5">
      <Label htmlFor={id}>{label}</Label>
      <Input
        id={id}
        type="number"
        inputMode="decimal"
        min={0}
        step={step ?? "1"}
        value={value}
        onChange={(e) => onChange(e.target.value === "" ? "" : Number(e.target.value))}
      />
      {hint && <p className="text-xs text-muted-foreground">{hint}</p>}
    </div>
  );
}

export default function StepDetails({ form, setForm, category }: { form: FormState; setForm: (f: FormState) => void; category: ApplicationCategory }) {
  const set = <K extends keyof FormState>(k: K, v: FormState[K]) => setForm({ ...form, [k]: v });
  const setProg = (i: number, patch: Partial<Programme>) => set("programmes", form.programmes.map((p, j) => (i === j ? { ...p, ...patch } : p)));
  const total = form.programmes.reduce((s, p) => s + (Number(p.intake) || 0), 0);

  return (
    <div className="space-y-4">
      <Panel
        title="Programmes and intake"
        description="Declare each programme for which approval is sought. These values are compared with AICTE records."
        actions={
          <Button
            size="sm"
            variant="outline"
            onClick={() => set("programmes", [...form.programmes, { level: "UG", programme: "Engineering & Technology", course: "", shift: "1", intake: "" }])}
          >
            <Plus className="mr-1 h-4 w-4" /> Add programme
          </Button>
        }
      >
        <div className="space-y-3">
          <div className="hidden grid-cols-[90px_minmax(0,1fr)_minmax(0,1.3fr)_80px_100px_36px] gap-2 text-xs font-semibold text-muted-foreground md:grid">
            <span>Level</span>
            <span>Programme</span>
            <span>Course</span>
            <span>Shift</span>
            <span>Intake</span>
            <span />
          </div>
          {form.programmes.map((p, i) => (
            <div key={i} className="grid grid-cols-2 gap-2 rounded-md border p-2 md:grid-cols-[90px_minmax(0,1fr)_minmax(0,1.3fr)_80px_100px_36px] md:border-0 md:p-0">
              <Select value={p.level} onValueChange={(v) => setProg(i, { level: v })}>
                <SelectTrigger aria-label="Level">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {["DIPLOMA", "UG", "PG", "PGDM"].map((l) => (
                    <SelectItem key={l} value={l}>
                      {l}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <Input aria-label="Programme" value={p.programme} onChange={(e) => setProg(i, { programme: e.target.value })} placeholder="Engineering & Technology" />
              <Input aria-label="Course" value={p.course} onChange={(e) => setProg(i, { course: e.target.value })} placeholder="e.g. Computer Science and Engineering" className="col-span-2 md:col-span-1" />
              <Select value={String(p.shift)} onValueChange={(v) => setProg(i, { shift: v })}>
                <SelectTrigger aria-label="Shift">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="1">1st</SelectItem>
                  <SelectItem value="2">2nd</SelectItem>
                </SelectContent>
              </Select>
              <Input
                aria-label="Intake"
                type="number"
                min={0}
                value={p.intake}
                onChange={(e) => setProg(i, { intake: e.target.value === "" ? "" : Number(e.target.value) })}
              />
              <Button
                variant="ghost"
                size="icon"
                className="h-10 w-9"
                disabled={form.programmes.length === 1}
                onClick={() => set("programmes", form.programmes.filter((_, j) => j !== i))}
                aria-label="Remove programme"
              >
                <Trash2 className="h-4 w-4" />
              </Button>
            </div>
          ))}
          <p className="text-right text-sm text-muted-foreground">
            Total intake <span className="tabular font-semibold text-foreground">{total}</span>
          </p>
        </div>
        {category === "INTAKE_INCREASE" && (
          <div className="mt-4 max-w-xs">
            <NumField id="proposedIntake" label="Proposed total intake" value={form.proposedIntake} onChange={(v) => set("proposedIntake", v)} hint="Total intake after the requested increase." />
          </div>
        )}
      </Panel>

      <div className="grid gap-4 lg:grid-cols-2">
        <Panel title="Faculty and students">
          <div className="grid gap-4 sm:grid-cols-2">
            <NumField id="facultyCount" label="Regular faculty (total)" value={form.facultyCount} onChange={(v) => set("facultyCount", v)} />
            <NumField id="studentCount" label="Sanctioned students (total)" value={form.studentCount} onChange={(v) => set("studentCount", v)} />
          </div>
          <p className="kv-label mb-2 mt-5">Cadre (optional)</p>
          <div className="grid grid-cols-3 gap-3">
            <NumField id="prof" label="Professors" value={form.cadre.professor} onChange={(v) => set("cadre", { ...form.cadre, professor: v })} />
            <NumField id="assoc" label="Assoc. Prof." value={form.cadre.associateProfessor} onChange={(v) => set("cadre", { ...form.cadre, associateProfessor: v })} />
            <NumField id="asst" label="Asst. Prof." value={form.cadre.assistantProfessor} onChange={(v) => set("cadre", { ...form.cadre, assistantProfessor: v })} />
          </div>
        </Panel>

        <Panel title="Land and building">
          <div className="grid gap-4 sm:grid-cols-2">
            <NumField id="land" label="Land area (acres)" step="0.01" value={form.landAreaAcres} onChange={(v) => set("landAreaAcres", v)} />
            <NumField id="built" label="Built-up area (sq m)" value={form.builtUpAreaSqm} onChange={(v) => set("builtUpAreaSqm", v)} />
            <div className="space-y-1.5">
              <Label htmlFor="loc">Location type</Label>
              <Select value={form.locationType} onValueChange={(v) => set("locationType", v)}>
                <SelectTrigger id="loc">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {["METRO", "URBAN", "RURAL", "HILLY"].map((l) => (
                    <SelectItem key={l} value={l}>
                      {l.charAt(0) + l.slice(1).toLowerCase()}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>
        </Panel>

        <Panel title="Fee and accreditation">
          <div className="space-y-4">
            <div className="space-y-1.5">
              <Label htmlFor="ter">TER / processing fee transaction ID</Label>
              <Input id="ter" className="mono" value={form.terTxnId} onChange={(e) => set("terTxnId", e.target.value)} placeholder="e.g. TER2026WR00123" />
            </div>
            <label className="flex items-center justify-between gap-3 rounded-md border px-3 py-2.5">
              <span>
                <span className="block text-sm font-medium">NBA accredited programme(s)</span>
                <span className="block text-xs text-muted-foreground">Claiming this adds the NBA certificate to your checklist.</span>
              </span>
              <Switch checked={form.nbaAccredited} onCheckedChange={(v) => set("nbaAccredited", v)} />
            </label>
            <label className="flex items-center justify-between gap-3 rounded-md border px-3 py-2.5">
              <span>
                <span className="block text-sm font-medium">NAAC accredited</span>
                <span className="block text-xs text-muted-foreground">Claiming this adds the NAAC certificate to your checklist.</span>
              </span>
              <Switch checked={form.naacAccredited} onCheckedChange={(v) => set("naacAccredited", v)} />
            </label>
          </div>
        </Panel>
      </div>
    </div>
  );
}
