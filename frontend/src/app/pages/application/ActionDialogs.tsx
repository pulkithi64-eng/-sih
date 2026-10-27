import { useEffect, useState } from "react";
import { Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Label } from "@/components/ui/label";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import { Textarea } from "@/components/ui/textarea";
import { AdvisoryNote } from "@/components/common/AdvisoryNote";
import { SeverityBadge } from "@/components/common/SeverityBadge";
import { useDecision, useObservation, useRectification } from "@/lib/hooks";
import { DECISION_LABEL, SEVERITY_ORDER } from "@/lib/labels";
import type { ApplicationDetail, Id } from "@/lib/types";
import { cn } from "@/lib/utils";

const MIN_NOTE = 10;

function NoteField({ value, onChange, label, placeholder, id }: { value: string; onChange: (v: string) => void; label: string; placeholder?: string; id: string }) {
  const short = value.trim().length > 0 && value.trim().length < MIN_NOTE;
  return (
    <div className="space-y-1.5">
      <Label htmlFor={id}>
        {label} <span className="text-red-700">*</span>
      </Label>
      <Textarea id={id} value={value} onChange={(e) => onChange(e.target.value)} placeholder={placeholder} rows={4} aria-invalid={short} />
      <p className={cn("text-xs", short ? "text-red-700" : "text-muted-foreground")}>
        {short ? `Please write at least ${MIN_NOTE} characters.` : "Recorded verbatim in the tamper-evident audit trail."}
      </p>
    </div>
  );
}

export function ObservationDialog({ app, open, onOpenChange }: { app: ApplicationDetail; open: boolean; onOpenChange: (o: boolean) => void }) {
  const [note, setNote] = useState("");
  const m = useObservation(app.id);
  useEffect(() => {
    if (open) setNote("");
  }, [open]);
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>Add observation</DialogTitle>
          <DialogDescription>Record a scrutiny observation for {app.applicationNo}. Observations are visible in the audit trail.</DialogDescription>
        </DialogHeader>
        <NoteField id="obs-note" label="Observation" value={note} onChange={setNote} placeholder="e.g. Fire NOC validity confirmed telephonically with district fire office." />
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button
            disabled={note.trim().length < MIN_NOTE || m.isPending}
            onClick={() => m.mutate(note.trim(), { onSuccess: () => onOpenChange(false) })}
          >
            {m.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
            Save observation
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

export function RectificationDialog({ app, open, onOpenChange }: { app: ApplicationDetail; open: boolean; onOpenChange: (o: boolean) => void }) {
  const openFindings = (app.findings ?? [])
    .filter((f) => f.status === "OPEN" || f.status === "ESCALATED" || f.status === "ACKNOWLEDGED")
    .sort((a, b) => SEVERITY_ORDER.indexOf(a.severity) - SEVERITY_ORDER.indexOf(b.severity));
  const [note, setNote] = useState("");
  const [sel, setSel] = useState<Set<string>>(new Set());
  const m = useRectification(app.id);
  useEffect(() => {
    if (open) {
      setNote("");
      setSel(new Set(openFindings.filter((f) => f.severity === "CRITICAL" || f.severity === "MAJOR").map((f) => String(f.id))));
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open]);
  const toggle = (id: Id) =>
    setSel((s) => {
      const n = new Set(s);
      const k = String(id);
      if (n.has(k)) n.delete(k);
      else n.add(k);
      return n;
    });
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-2xl">
        <DialogHeader>
          <DialogTitle>Request rectification</DialogTitle>
          <DialogDescription>
            The institution will be asked to respond to the selected findings. The application moves to “Rectification requested”.
          </DialogDescription>
        </DialogHeader>
        <div className="space-y-4">
          <div>
            <div className="mb-1.5 flex items-center justify-between">
              <Label>Findings to include</Label>
              <span className="text-xs text-muted-foreground">
                {sel.size} of {openFindings.length} selected
              </span>
            </div>
            <div className="max-h-56 overflow-y-auto rounded-md border">
              {openFindings.length === 0 ? (
                <p className="p-3 text-sm text-muted-foreground">No open findings. You can still send a general request.</p>
              ) : (
                openFindings.map((f) => (
                  <label key={f.id} className="flex cursor-pointer items-start gap-3 border-b px-3 py-2 last:border-0 hover:bg-muted/40">
                    <Checkbox checked={sel.has(String(f.id))} onCheckedChange={() => toggle(f.id)} className="mt-0.5" />
                    <span className="min-w-0 flex-1">
                      <span className="flex items-center gap-2">
                        <SeverityBadge severity={f.severity} />
                        <span className="truncate text-sm font-medium">{f.title}</span>
                      </span>
                      <span className="mt-0.5 line-clamp-1 block text-xs text-muted-foreground">{f.reason}</span>
                    </span>
                  </label>
                ))
              )}
            </div>
          </div>
          <NoteField
            id="rect-note"
            label="Instructions to the institution"
            value={note}
            onChange={setNote}
            placeholder="Describe what must be corrected or re-submitted, and by when."
          />
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button
            disabled={note.trim().length < MIN_NOTE || m.isPending}
            onClick={() =>
              m.mutate(
                { note: note.trim(), findingIds: openFindings.filter((f) => sel.has(String(f.id))).map((f) => f.id) },
                { onSuccess: () => onOpenChange(false) },
              )
            }
          >
            {m.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
            Send request
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

const RD_ACTIONS = ["APPROVE_FOR_EOA", "ISSUE_DEFICIENCY_LETTER", "ORDER_INSPECTION", "REJECT"];
const ACTION_HINT: Record<string, string> = {
  APPROVE_FOR_EOA: "Grant approval for the academic year.",
  ISSUE_DEFICIENCY_LETTER: "Communicate deficiencies formally; institution must comply.",
  ORDER_INSPECTION: "Physical verification by an expert committee before deciding.",
  REJECT: "Decline the application with reasons.",
};

export function DecisionDialog({
  app,
  open,
  onOpenChange,
  mode,
}: {
  app: ApplicationDetail;
  open: boolean;
  onOpenChange: (o: boolean) => void;
  mode: "decide" | "recommend";
}) {
  const actions = mode === "decide" ? RD_ACTIONS : RD_ACTIONS.map((a) => `RECOMMEND_${a}`);
  const [action, setAction] = useState<string>("");
  const [note, setNote] = useState("");
  const [ack, setAck] = useState(false);
  const [confirming, setConfirming] = useState(false);
  const m = useDecision(app.id);
  useEffect(() => {
    if (open) {
      setAction("");
      setNote("");
      setAck(false);
      setConfirming(false);
    }
  }, [open]);
  const critical = app.findings.filter((f) => f.severity === "CRITICAL" && !["RECTIFIED", "DISMISSED"].includes(f.status)).length;
  const blocked = critical > 0 && action.endsWith("APPROVE_FOR_EOA");
  const valid = !!action && note.trim().length >= MIN_NOTE && ack && !blocked;
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-xl">
        <DialogHeader>
          <DialogTitle>{mode === "decide" ? "Record decision" : "Record recommendation"}</DialogTitle>
          <DialogDescription>
            {app.applicationNo} · {app.institution?.name}
          </DialogDescription>
        </DialogHeader>
        {!confirming ? (
          <div className="space-y-4">
            <RadioGroup value={action} onValueChange={setAction} className="grid gap-2 sm:grid-cols-2" aria-label="Action">
              {actions.map((a) => {
                const base = a.replace(/^RECOMMEND_/, "");
                return (
                  <Label
                    key={a}
                    htmlFor={`act-${a}`}
                    className={cn(
                      "flex cursor-pointer items-start gap-2.5 rounded-md border p-3 font-normal hover:bg-muted/40",
                      action === a && "border-primary-600 bg-navy-50",
                    )}
                  >
                    <RadioGroupItem id={`act-${a}`} value={a} className="mt-0.5" />
                    <span>
                      <span className="block text-sm font-medium">{DECISION_LABEL[a] ?? a}</span>
                      <span className="block text-xs text-muted-foreground">{ACTION_HINT[base]}</span>
                    </span>
                  </Label>
                );
              })}
            </RadioGroup>
            {critical > 0 && action.endsWith("APPROVE_FOR_EOA") && (
              <p className="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-xs text-red-800">
                Approval is blocked by {critical} unresolved critical finding{critical === 1 ? "" : "s"}. A reviewer must confirm rectification
                or dismiss each with an evidence-based reason. Acknowledgement and escalation do not resolve findings.
              </p>
            )}
            <NoteField id="dec-note" label="Reasoned note" value={note} onChange={setNote} placeholder="Summarise the evidence considered and the basis for this action." />
            <label className="flex items-start gap-2.5 text-sm">
              <Checkbox checked={ack} onCheckedChange={(v) => setAck(v === true)} className="mt-0.5" />
              <span>
                I have reviewed the documents and evidence myself. I understand that VeriSense findings and scores are advisory and do not
                determine this {mode === "decide" ? "decision" : "recommendation"}.
              </span>
            </label>
          </div>
        ) : (
          <div className="space-y-3">
            <div className="rounded-md border bg-muted/40 p-3 text-sm">
              <p className="kv-label">Action</p>
              <p className="mt-0.5 font-semibold">{DECISION_LABEL[action] ?? action}</p>
              <p className="kv-label mt-3">Note</p>
              <p className="mt-0.5 whitespace-pre-wrap">{note.trim()}</p>
            </div>
            <AdvisoryNote>
              AI outputs are advisory. This {mode === "decide" ? "decision" : "recommendation"} is yours and will be recorded under your name in
              the audit trail. It cannot be edited afterwards.
            </AdvisoryNote>
          </div>
        )}
        <DialogFooter>
          {confirming ? (
            <>
              <Button variant="outline" onClick={() => setConfirming(false)}>
                Back
              </Button>
              <Button disabled={m.isPending || !valid} onClick={() => m.mutate({ action, note: note.trim() }, { onSuccess: () => onOpenChange(false) })}>
                {m.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                Confirm and record
              </Button>
            </>
          ) : (
            <>
              <Button variant="outline" onClick={() => onOpenChange(false)}>
                Cancel
              </Button>
              <Button disabled={!valid} onClick={() => setConfirming(true)}>
                Review &amp; confirm
              </Button>
            </>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
