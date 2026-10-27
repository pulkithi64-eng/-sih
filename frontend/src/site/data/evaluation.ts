// Generated alongside samples/evaluation.json by backend/evaluate.py.
import measured from "./evaluation.generated.json";

export type EvalCriterion = {
  key: string;
  name: string;
  measures: string;
  method: string;
  metric: string;
};

export const EVAL_CRITERIA: EvalCriterion[] = [
  {
    key: "extraction",
    name: "Extraction accuracy",
    measures: "How often key fields (reference number, dates, issuer, amounts, intake) are read correctly.",
    method: "Each synthetic document is generated with known ground-truth field values; the pipeline's extracted values are compared after normalisation.",
    metric: "Normalised field-match accuracy; classification accuracy per document type",
  },
  {
    key: "validation",
    name: "Validation accuracy",
    measures: "Whether the rule engine raises the findings each scenario is designed to contain, and no others.",
    method: "Each free-text scenario expectation is matched to findings by kind and target. Labels are incomplete, so this is a coverage proxy, not a full accuracy estimate.",
    metric: "Expected-scenario coverage; precision/F1 require exhaustive labels",
  },
  {
    key: "anomaly",
    name: "Anomaly detection performance",
    measures: "Ability to tell tampered or duplicated documents from clean ones.",
    method: "Clean documents and tampered variants (edited regions, editing-software metadata, duplicates) are run through forensics.",
    metric: "Precision and recall on the tampered set; false-positive rate on the clean set",
  },
  {
    key: "verification",
    name: "Source-verification success rate",
    measures: "Share of verifiable documents for which the source returns a conclusive result.",
    method: "Verifiable documents are checked against the simulated authorities, with some sources deliberately offline.",
    metric: "Conclusive results / verifiable documents; distribution across the six states",
  },
  {
    key: "discrepancy",
    name: "Discrepancy reliability",
    measures: "Whether mismatches reported against source or records are real.",
    method: "Documents with planted field differences are compared with source records; reported mismatches are checked against the planted ones.",
    metric: "Source-mismatch precision; record-mismatch precision awaits independent labels",
  },
  {
    key: "time",
    name: "Average verification time",
    measures: "Time from upload to a complete validation report.",
    method: "Wall-clock time of the document pipeline per file and of the full application validation, on a laptop CPU.",
    metric: "Mean and 95th percentile seconds per document and per application",
  },
  {
    key: "alerts",
    name: "Alert timeliness",
    measures: "Delay between a critical condition being detectable and the officer being alerted.",
    method: "Alerts are created inside the same validation transaction that writes the finding.",
    metric: "Seconds from submission to alert",
  },
  {
    key: "effort",
    name: "Reduction in manual effort",
    measures: "Officer time saved on preliminary scrutiny.",
    method: "Estimated from the number of checks performed automatically per application multiplied by an assumed manual time per check; stated as an estimate.",
    metric: "Estimated hours saved per application",
  },
];

export type EvalResult = { headline: string; detail?: string };

/** Filled from samples/evaluation.json. */
export const EVAL_RESULTS: Record<string, EvalResult> = measured.results;

export const EVAL_DATASET: { generatedAt?: string; summary: string } = {
  summary: measured.dataset.summary,
  generatedAt: measured.generatedAt,
};
