import { useMemo, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import {
  Building2,
  Calendar,
  CheckCircle2,
  ExternalLink,
  GraduationCap,
  Layers,
  MapPin,
  Pencil,
  Plus,
  RefreshCw,
  Search,
  ShieldAlert,
  Users,
} from "lucide-react";
import { toast } from "sonner";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Textarea } from "@/components/ui/textarea";
import { EmptyState, ErrorState } from "@/components/common/EmptyState";
import { KpiCard } from "@/components/common/KpiCard";
import { PageHeader } from "@/components/common/PageHeader";
import { RiskBandPill } from "@/components/common/SeverityBadge";
import { StatusBadge } from "@/components/common/StatusBadge";
import {
  useCreateInstitution,
  useInstitution,
  useInstitutionOverview,
  useInstitutions,
  useUpdateInstitution,
} from "@/lib/hooks";
import { REGION_LABEL } from "@/lib/labels";
import type { Institution, Region } from "@/lib/types";
import { cn } from "@/lib/utils";
import { isAdmin, isReviewer, useAuth } from "../auth";
import { Panel } from "../components/Panel";
import { PageSkeleton } from "../components/Skeletons";

const REGIONS: Region[] = ["NR", "WR", "SR", "ER", "CR", "SWR", "SER", "NWR"];

const INST_TYPES = [
  "Private-Self Financing",
  "Government",
  "Govt Aided",
  "University Managed-Govt",
  "Deemed to be University",
];

export default function InstitutionsPage() {
  const { user } = useAuth();
  const [sp, setSp] = useSearchParams();
  const qRegion = sp.get("region") ?? undefined;
  const qType = sp.get("type") ?? undefined;
  const qSearch = sp.get("q") ?? "";

  const [search, setSearch] = useState(qSearch);
  const [selectedInstId, setSelectedInstId] = useState<string | number | null>(null);
  const [createOpen, setCreateOpen] = useState(false);
  const [editInst, setEditInst] = useState<Institution | null>(null);

  const overview = useInstitutionOverview();
  const institutionsQ = useInstitutions({
    region: qRegion,
    type: qType,
    q: qSearch || undefined,
  });

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    const next = new URLSearchParams(sp);
    if (search.trim()) next.set("q", search.trim());
    else next.delete("q");
    setSp(next, { replace: true });
  };

  const setFilter = (key: string, val: string | null) => {
    const next = new URLSearchParams(sp);
    if (!val || val === "ALL") next.delete(key);
    else next.set(key, val);
    setSp(next, { replace: true });
  };

  const clearFilters = () => {
    setSearch("");
    setSp(new URLSearchParams(), { replace: true });
  };

  const insts = institutionsQ.data ?? [];
  const canManage = isAdmin(user?.role) || user?.role === "REGIONAL_DIRECTOR";

  return (
    <div className="space-y-6">
      <PageHeader
        title={user?.role === "INSTITUTION" ? "My institution" : "Institutions"}
        description={user?.role === "INSTITUTION" ? "Your institution's profile and recorded application information." : "Find an institution and review its recorded information."}
        eyebrow={
          <Badge variant="outline" className="font-mono text-xs">
            {insts.length} {insts.length === 1 ? "Institution" : "Institutions"}
          </Badge>
        }
        actions={
          canManage && (
            <Button size="sm" onClick={() => setCreateOpen(true)} className="gap-1.5">
              <Plus className="h-4 w-4" />
              Register Institution
            </Button>
          )
        }
      />

      {/* Aggregate KPI Cards */}
      {overview.data && (
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4 lg:grid-cols-5">
          <KpiCard
            label="Total Institutions"
            value={overview.data.totalInstitutions}
            icon={Building2}
            hint="Under jurisdiction"
          />
          <KpiCard
            label="Approved Programmes"
            value={overview.data.totalApprovedProgrammes}
            icon={GraduationCap}
            hint="Accredited technical degrees"
          />
          <KpiCard
            label="Sanctioned Intake"
            value={overview.data.totalSanctionedIntake.toLocaleString()}
            icon={Users}
            hint="Total student seats"
          />
          <KpiCard
            label="Recorded Faculty"
            value={overview.data.totalRecordedFaculty.toLocaleString()}
            icon={Layers}
            hint="On official AICTE roster"
          />
          <KpiCard
            label="High Risk Profile"
            value={overview.data.highRiskInstitutions}
            icon={ShieldAlert}
            tone={overview.data.highRiskInstitutions > 0 ? "danger" : "default"}
            hint="Critical findings pending"
          />
        </div>
      )}

      {/* Filter and Search Bar */}
      <Panel className="p-4">
        <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
          <form onSubmit={handleSearch} className="flex flex-1 items-center gap-2">
            <div className="relative flex-1 max-w-md">
              <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
              <Input
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Search by Institution Name, Permanent ID, or City..."
                className="pl-9 text-sm"
              />
            </div>
            <Button type="submit" variant="secondary" size="sm">
              Search
            </Button>
          </form>

          <div className="flex flex-wrap items-center gap-2">
            {/* Region Filter (Admin only) */}
            {isAdmin(user?.role) && (
              <Select value={qRegion ?? "ALL"} onValueChange={(v) => setFilter("region", v)}>
                <SelectTrigger className="w-[140px] text-xs h-9">
                  <SelectValue placeholder="Region" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="ALL">All Regions</SelectItem>
                  {REGIONS.map((r) => (
                    <SelectItem key={r} value={r}>
                      {r} — {REGION_LABEL[r] ?? r}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            )}

            {/* Type Filter */}
            <Select value={qType ?? "ALL"} onValueChange={(v) => setFilter("type", v)}>
              <SelectTrigger className="w-[160px] text-xs h-9">
                <SelectValue placeholder="Type" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="ALL">All Types</SelectItem>
                {INST_TYPES.map((t) => (
                  <SelectItem key={t} value={t}>
                    {t}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>

            {(qRegion || qType || qSearch) && (
              <Button variant="ghost" size="sm" onClick={clearFilters} className="text-xs text-muted-foreground">
                Reset
              </Button>
            )}
          </div>
        </div>
      </Panel>

      {/* Institutions Table */}
      {institutionsQ.isLoading ? (
        <PageSkeleton />
      ) : institutionsQ.isError ? (
        <ErrorState error={institutionsQ.error} onRetry={() => institutionsQ.refetch()} />
      ) : insts.length === 0 ? (
        <EmptyState
          icon={Building2}
          title="No institutions found"
          description="Try modifying search criteria or region filters."
          action={
            (qRegion || qType || qSearch) && (
              <Button variant="outline" size="sm" onClick={clearFilters}>
                Clear filters
              </Button>
            )
          }
        />
      ) : (
        <Panel className="overflow-hidden p-0">
          <div className="overflow-x-auto">
            <Table>
              <TableHeader className="bg-muted/40">
                <TableRow>
                  <TableHead className="w-[120px] font-semibold text-xs">Permanent ID</TableHead>
                  <TableHead className="font-semibold text-xs">Institution</TableHead>
                  <TableHead className="font-semibold text-xs">Region / Location</TableHead>
                  <TableHead className="text-center font-semibold text-xs">Programmes</TableHead>
                  <TableHead className="text-center font-semibold text-xs">Intake</TableHead>
                  <TableHead className="text-center font-semibold text-xs">Faculty</TableHead>
                  <TableHead className="font-semibold text-xs">Applications</TableHead>
                  <TableHead className="font-semibold text-xs">Risk Profile</TableHead>
                  <TableHead className="text-right font-semibold text-xs">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {insts.map((i) => {
                  const s = i.stats;
                  return (
                    <TableRow key={i.id} className="hover:bg-muted/30">
                      <TableCell className="font-mono text-xs font-semibold text-primary">
                        {i.permanentId}
                      </TableCell>
                      <TableCell>
                        <div className="font-medium text-sm text-foreground">{i.name}</div>
                        <div className="text-xs text-muted-foreground flex items-center gap-1.5 mt-0.5">
                          <span>{i.type}</span>
                          <span>•</span>
                          <span>Est. {i.establishedYear}</span>
                          {s?.naacGrade && (
                            <>
                              <span>•</span>
                              <span className="text-emerald-700 font-semibold">NAAC {s.naacGrade}</span>
                            </>
                          )}
                        </div>
                      </TableCell>
                      <TableCell>
                        <div className="text-xs font-medium text-foreground">
                          {i.city}, {i.state}
                        </div>
                        <div className="text-2xs text-muted-foreground mt-0.5 flex items-center gap-1">
                          <MapPin className="h-3 w-3 text-muted-foreground/70" />
                          <span>Region: {i.region}</span>
                        </div>
                      </TableCell>
                      <TableCell className="text-center tabular font-medium text-xs">
                        {s?.programmesCount ?? 0}
                      </TableCell>
                      <TableCell className="text-center tabular font-medium text-xs">
                        {s?.totalIntake ? s.totalIntake.toLocaleString() : "—"}
                      </TableCell>
                      <TableCell className="text-center tabular font-medium text-xs">
                        {s?.facultyCount ?? 0}
                      </TableCell>
                      <TableCell>
                        <div className="text-xs">
                          <span className="font-semibold tabular">{s?.applicationsCount ?? 0}</span> total
                        </div>
                        {s?.latestStatus && s.latestStatus !== "NO_APPLICATIONS" && (
                          <div className="mt-1">
                            <StatusBadge status={s.latestStatus as any} size="sm" />
                          </div>
                        )}
                      </TableCell>
                      <TableCell>
                        <RiskBandPill band={s?.riskBand ?? "LOW"} />
                        {s?.openFindings && s.openFindings > 0 ? (
                          <div className="text-2xs text-amber-700 font-medium mt-1">
                            {s.openFindings} finding{s.openFindings > 1 ? "s" : ""}
                          </div>
                        ) : null}
                      </TableCell>
                      <TableCell className="text-right">
                        <div className="flex items-center justify-end gap-1.5">
                          <Button
                            variant="outline"
                            size="sm"
                            className="h-7 text-xs px-2"
                            onClick={() => setSelectedInstId(i.id)}
                          >
                            Details
                          </Button>
                          {isAdmin(user?.role) && (
                            <Button
                              variant="ghost"
                              size="sm"
                              className="h-7 w-7 p-0"
                              onClick={() => setEditInst(i)}
                              title="Edit Institution Profile"
                            >
                              <Pencil className="h-3.5 w-3.5" />
                            </Button>
                          )}
                        </div>
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          </div>
        </Panel>
      )}

      {/* Institution Details Dialog */}
      {selectedInstId && (
        <InstitutionDetailDialog
          institutionId={selectedInstId}
          open={!!selectedInstId}
          onClose={() => setSelectedInstId(null)}
        />
      )}

      {/* Register New Institution Dialog */}
      {createOpen && <CreateInstitutionDialog open={createOpen} onClose={() => setCreateOpen(false)} />}

      {/* Edit Institution Dialog */}
      {editInst && <EditInstitutionDialog inst={editInst} open={!!editInst} onClose={() => setEditInst(null)} />}
    </div>
  );
}

function InstitutionDetailDialog({
  institutionId,
  open,
  onClose,
}: {
  institutionId: string | number;
  open: boolean;
  onClose: () => void;
}) {
  const q = useInstitution(institutionId);
  const inst = q.data;

  return (
    <Dialog open={open} onOpenChange={(o) => !o && onClose()}>
      <DialogContent className="max-w-3xl max-h-[90vh] overflow-y-auto">
        {q.isLoading || !inst ? (
          <PageSkeleton />
        ) : (
          <>
            <DialogHeader>
              <div className="flex items-start justify-between gap-4">
                <div>
                  <div className="flex items-center gap-2">
                    <Badge variant="outline" className="font-mono text-xs text-primary">
                      {inst.permanentId}
                    </Badge>
                    <Badge variant="secondary" className="text-xs">
                      {inst.region} Region
                    </Badge>
                  </div>
                  <DialogTitle className="mt-2 text-xl font-bold text-foreground">{inst.name}</DialogTitle>
                  <DialogDescription className="text-xs text-muted-foreground mt-1">
                    {inst.type} • Established in {inst.establishedYear} • Trust: {inst.trustName}
                  </DialogDescription>
                </div>
                {inst.stats && <RiskBandPill band={inst.stats.riskBand} />}
              </div>
            </DialogHeader>

            <Tabs defaultValue="overview" className="mt-4">
              <TabsList className="grid grid-cols-4 w-full text-xs">
                <TabsTrigger value="overview">Overview</TabsTrigger>
                <TabsTrigger value="programmes">Programmes ({inst.stats?.programmesCount ?? 0})</TabsTrigger>
                <TabsTrigger value="faculty">Faculty ({inst.stats?.facultyCount ?? 0})</TabsTrigger>
                <TabsTrigger value="applications">Applications ({inst.stats?.applicationsCount ?? 0})</TabsTrigger>
              </TabsList>

              {/* Overview Tab */}
              <TabsContent value="overview" className="space-y-4 pt-3">
                <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
                  <div className="rounded-lg border p-3 bg-muted/20">
                    <div className="text-2xs font-semibold text-muted-foreground uppercase">Campus Location</div>
                    <div className="font-medium text-sm mt-1 text-foreground">
                      {inst.city}, {inst.state}
                    </div>
                    <div className="text-xs text-muted-foreground mt-0.5">{inst.address}</div>
                  </div>
                  <div className="rounded-lg border p-3 bg-muted/20">
                    <div className="text-2xs font-semibold text-muted-foreground uppercase">Campus GPS</div>
                    <div className="font-mono text-sm mt-1 text-foreground">
                      {inst.campusGps ? `${inst.campusGps.lat.toFixed(4)}, ${inst.campusGps.lng.toFixed(4)}` : "Not Tagged"}
                    </div>
                    <div className="text-xs text-muted-foreground mt-0.5">Verified Coordinates</div>
                  </div>
                  <div className="rounded-lg border p-3 bg-muted/20">
                    <div className="text-2xs font-semibold text-muted-foreground uppercase">Land Area</div>
                    <div className="font-medium text-sm mt-1 text-foreground">
                      {inst.stats?.landAreaAcres ? `${inst.stats.landAreaAcres} Acres` : "—"}
                    </div>
                    <div className="text-xs text-muted-foreground mt-0.5">Title Deed Recorded</div>
                  </div>
                </div>

                <div className="rounded-lg border p-4 bg-card">
                  <h4 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-3">
                    Scrutiny & Compliance Summary
                  </h4>
                  <div className="grid grid-cols-3 gap-4 text-center">
                    <div>
                      <div className="text-2xl font-bold text-foreground tabular">{inst.stats?.averageCompliance ?? 0}%</div>
                      <div className="text-xs text-muted-foreground mt-0.5">Avg Compliance</div>
                    </div>
                    <div>
                      <div className="text-2xl font-bold text-amber-600 tabular">{inst.stats?.openFindings ?? 0}</div>
                      <div className="text-xs text-muted-foreground mt-0.5">Open Deficiencies</div>
                    </div>
                    <div>
                      <div className="text-2xl font-bold text-foreground tabular">{inst.stats?.totalIntake?.toLocaleString() ?? 0}</div>
                      <div className="text-xs text-muted-foreground mt-0.5">Total Intake Seats</div>
                    </div>
                  </div>
                </div>
              </TabsContent>

              {/* Programmes Tab */}
              <TabsContent value="programmes" className="pt-3">
                <ProgrammesList institutionId={institutionId} />
              </TabsContent>

              {/* Faculty Tab */}
              <TabsContent value="faculty" className="pt-3">
                <FacultyList institutionId={institutionId} />
              </TabsContent>

              {/* Applications Tab */}
              <TabsContent value="applications" className="pt-3">
                <ApplicationsList institutionId={institutionId} />
              </TabsContent>
            </Tabs>

            <DialogFooter className="mt-4 border-t pt-3">
              <Button variant="outline" onClick={onClose} size="sm">
                Close
              </Button>
            </DialogFooter>
          </>
        )}
      </DialogContent>
    </Dialog>
  );
}

function ProgrammesList({ institutionId }: { institutionId: string | number }) {
  const q = useInstitution(institutionId);
  const inst = q.data as any;
  const progs = inst?.records?.approvedProgrammes ?? [];

  if (progs.length === 0) {
    return <EmptyState title="No approved programmes on record" />;
  }

  return (
    <div className="border rounded-lg overflow-hidden">
      <Table>
        <TableHeader className="bg-muted/40">
          <TableRow>
            <TableHead className="text-xs">Level</TableHead>
            <TableHead className="text-xs">Programme / Course</TableHead>
            <TableHead className="text-xs">Shift</TableHead>
            <TableHead className="text-right text-xs">Approved Intake</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {progs.map((p: any, idx: number) => (
            <TableRow key={idx}>
              <TableCell className="font-semibold text-xs">{p.level}</TableCell>
              <TableCell className="text-xs">
                <div className="font-medium text-foreground">{p.course}</div>
                <div className="text-2xs text-muted-foreground">{p.programme}</div>
              </TableCell>
              <TableCell className="text-xs text-muted-foreground">{p.shift || "Regular"}</TableCell>
              <TableCell className="text-right font-mono font-semibold text-xs tabular">{p.intake} seats</TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}

function FacultyList({ institutionId }: { institutionId: string | number }) {
  const q = useInstitution(institutionId);
  const inst = q.data as any;
  const faculty = inst?.records?.faculty ?? [];

  if (faculty.length === 0) {
    return <EmptyState title="No faculty records registered" />;
  }

  return (
    <div className="border rounded-lg overflow-hidden">
      <Table>
        <TableHeader className="bg-muted/40">
          <TableRow>
            <TableHead className="text-xs">Faculty ID</TableHead>
            <TableHead className="text-xs">Name & Designation</TableHead>
            <TableHead className="text-xs">Department</TableHead>
            <TableHead className="text-xs">PAN (Masked)</TableHead>
            <TableHead className="text-right text-xs">Joining Date</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {faculty.map((f: any, idx: number) => (
            <TableRow key={idx}>
              <TableCell className="font-mono text-2xs text-muted-foreground">{f.facultyId}</TableCell>
              <TableCell className="text-xs">
                <div className="font-medium text-foreground">{f.name}</div>
                <div className="text-2xs text-muted-foreground">{f.designation}</div>
              </TableCell>
              <TableCell className="text-xs text-muted-foreground">{f.department}</TableCell>
              <TableCell className="font-mono text-xs">{f.panMasked || "—"}</TableCell>
              <TableCell className="text-right text-xs text-muted-foreground">{f.joiningDate}</TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}

function ApplicationsList({ institutionId }: { institutionId: string | number }) {
  const q = useInstitution(institutionId);
  const inst = q.data;
  const latestId = inst?.stats?.latestAppId;

  return (
    <div className="space-y-3">
      <div className="rounded-lg border p-4 bg-muted/20 flex items-center justify-between">
        <div>
          <div className="text-xs font-semibold text-foreground">Total Applications on File</div>
          <div className="text-sm text-muted-foreground mt-0.5">
            {inst?.stats?.applicationsCount ?? 0} application(s) recorded in AICTE scrutiny system.
          </div>
        </div>
        {latestId && (
          <Button asChild size="sm" variant="default" className="gap-1.5 text-xs">
            <Link to={`/portal/applications/${latestId}`}>
              <span>Open Latest</span>
              <ExternalLink className="h-3.5 w-3.5" />
            </Link>
          </Button>
        )}
      </div>
      <div className="text-xs text-center text-muted-foreground pt-2">
        <Link to={`/portal/applications?q=${inst?.permanentId}`} className="text-primary hover:underline font-medium">
          View all applications in full scrutiny queue →
        </Link>
      </div>
    </div>
  );
}

function CreateInstitutionDialog({ open, onClose }: { open: boolean; onClose: () => void }) {
  const m = useCreateInstitution();
  const [permanentId, setPermanentId] = useState("");
  const [name, setName] = useState("");
  const [instType, setInstType] = useState("Private-Self Financing");
  const [region, setRegion] = useState<Region>("WR");
  const [state, setState] = useState("");
  const [city, setCity] = useState("");
  const [year, setYear] = useState(new Date().getFullYear());
  const [trust, setTrust] = useState("");
  const [address, setAddress] = useState("");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!permanentId.trim() || !name.trim()) {
      toast.error("Permanent ID and Name are required");
      return;
    }
    m.mutate(
      {
        permanentId: permanentId.trim(),
        name: name.trim(),
        type: instType,
        region,
        state: state.trim(),
        city: city.trim(),
        establishedYear: Number(year),
        trustName: trust.trim(),
        address: address.trim(),
      },
      {
        onSuccess: () => {
          onClose();
        },
      }
    );
  };

  return (
    <Dialog open={open} onOpenChange={(o) => !o && onClose()}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle>Register New Institution</DialogTitle>
          <DialogDescription>
            Add a new technical institution to the regulatory jurisdiction.
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="space-y-3.5 pt-2">
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1">
              <Label className="text-xs">Permanent ID *</Label>
              <Input
                placeholder="1-XXXXXXXXXX"
                value={permanentId}
                onChange={(e) => setPermanentId(e.target.value)}
                required
              />
            </div>
            <div className="space-y-1">
              <Label className="text-xs">Region *</Label>
              <Select value={region} onValueChange={(v) => setRegion(v as Region)}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {REGIONS.map((r) => (
                    <SelectItem key={r} value={r}>
                      {r} — {REGION_LABEL[r] ?? r}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>

          <div className="space-y-1">
            <Label className="text-xs">Institution Name *</Label>
            <Input
              placeholder="e.g. Apex Institute of Technology"
              value={name}
              onChange={(e) => setName(e.target.value)}
              required
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1">
              <Label className="text-xs">Institution Type</Label>
              <Select value={instType} onValueChange={setInstType}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {INST_TYPES.map((t) => (
                    <SelectItem key={t} value={t}>
                      {t}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-1">
              <Label className="text-xs">Established Year</Label>
              <Input
                type="number"
                value={year}
                onChange={(e) => setYear(Number(e.target.value))}
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1">
              <Label className="text-xs">City</Label>
              <Input value={city} onChange={(e) => setCity(e.target.value)} />
            </div>
            <div className="space-y-1">
              <Label className="text-xs">State</Label>
              <Input value={state} onChange={(e) => setState(e.target.value)} />
            </div>
          </div>

          <div className="space-y-1">
            <Label className="text-xs">Trust / Society Name</Label>
            <Input value={trust} onChange={(e) => setTrust(e.target.value)} />
          </div>

          <div className="space-y-1">
            <Label className="text-xs">Address</Label>
            <Textarea
              rows={2}
              value={address}
              onChange={(e) => setAddress(e.target.value)}
              placeholder="Campus postal address"
            />
          </div>

          <DialogFooter className="pt-3">
            <Button type="button" variant="outline" onClick={onClose} size="sm">
              Cancel
            </Button>
            <Button type="submit" size="sm" disabled={m.isPending}>
              {m.isPending ? "Registering..." : "Register Institution"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

function EditInstitutionDialog({
  inst,
  open,
  onClose,
}: {
  inst: Institution;
  open: boolean;
  onClose: () => void;
}) {
  const m = useUpdateInstitution(inst.id);
  const [name, setName] = useState(inst.name);
  const [instType, setInstType] = useState(inst.type);
  const [state, setState] = useState(inst.state);
  const [city, setCity] = useState(inst.city);
  const [trust, setTrust] = useState(inst.trustName);
  const [address, setAddress] = useState(inst.address);

  const handleUpdate = (e: React.FormEvent) => {
    e.preventDefault();
    m.mutate(
      {
        name: name.trim(),
        type: instType,
        state: state.trim(),
        city: city.trim(),
        trustName: trust.trim(),
        address: address.trim(),
      },
      {
        onSuccess: () => {
          onClose();
        },
      }
    );
  };

  return (
    <Dialog open={open} onOpenChange={(o) => !o && onClose()}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle>Edit Institution Profile</DialogTitle>
          <DialogDescription>
            Update details for {inst.permanentId} ({inst.name}).
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleUpdate} className="space-y-3.5 pt-2">
          <div className="space-y-1">
            <Label className="text-xs">Institution Name</Label>
            <Input value={name} onChange={(e) => setName(e.target.value)} required />
          </div>

          <div className="space-y-1">
            <Label className="text-xs">Institution Type</Label>
            <Select value={instType} onValueChange={setInstType}>
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {INST_TYPES.map((t) => (
                  <SelectItem key={t} value={t}>
                    {t}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1">
              <Label className="text-xs">City</Label>
              <Input value={city} onChange={(e) => setCity(e.target.value)} />
            </div>
            <div className="space-y-1">
              <Label className="text-xs">State</Label>
              <Input value={state} onChange={(e) => setState(e.target.value)} />
            </div>
          </div>

          <div className="space-y-1">
            <Label className="text-xs">Trust / Society Name</Label>
            <Input value={trust} onChange={(e) => setTrust(e.target.value)} />
          </div>

          <div className="space-y-1">
            <Label className="text-xs">Campus Address</Label>
            <Textarea rows={2} value={address} onChange={(e) => setAddress(e.target.value)} />
          </div>

          <DialogFooter className="pt-3">
            <Button type="button" variant="outline" onClick={onClose} size="sm">
              Cancel
            </Button>
            <Button type="submit" size="sm" disabled={m.isPending}>
              {m.isPending ? "Saving..." : "Save Changes"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
