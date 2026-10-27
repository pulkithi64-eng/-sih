import type { Application } from "./types";

export const EDITABLE_STATUSES = new Set(["DRAFT", "RECTIFICATION_REQUESTED", "DEFICIENCIES_FLAGGED"]);

export function institutionNextAction(application: Application) {
  const base = `/portal/applications/${application.id}`;
  if (application.status === "RECTIFICATION_REQUESTED" || application.status === "DEFICIENCIES_FLAGGED") {
    return { label: "Correct application", to: `${base}/edit?step=respond`, description: "Read the findings, add your response and upload corrected documents." };
  }
  if (application.status === "DRAFT") {
    return { label: "Upload documents", to: `${base}/edit?step=documents`, description: "Upload the checklist documents, check the results and submit for review." };
  }
  return { label: "View progress", to: base, description: application.status === "DECIDED" ? "Read the decision and download the report." : "Your application is with the review team. Check here for updates." };
}

export function applicationStage(application: Application) {
  if (application.status === "DECIDED") return 4;
  if (["RECOMMENDED", "INSPECTION_ORDERED"].includes(application.status)) return 3;
  if (application.status !== "DRAFT") return 2;
  return application.counts?.documents ? 1 : 0;
}

export function verificationNextStep(status: string) {
  const steps: Record<string, string> = {
    VERIFIED: "Continue the checklist. A verified document does not approve the application.",
    MISMATCH_DETECTED: "Compare the highlighted values with the original. Correct the document or request confirmation from the issuer.",
    EXPIRED: "Provide a current document or ask the reviewer to confirm an applicable exception.",
    VERIFICATION_PENDING: "The issuer check is pending. Check again later or provide evidence for a reviewer.",
    SOURCE_UNAVAILABLE: "The issuer service could not be reached. Retry later; this is not evidence of fraud.",
    MANUAL_REVIEW_REQUIRED: "A reviewer must inspect the original and confirm the supporting evidence.",
    NOT_APPLICABLE: "Review this institution-provided evidence against the relevant checklist and rules.",
  };
  return steps[status] ?? "Ask a reviewer to check the original document.";
}
