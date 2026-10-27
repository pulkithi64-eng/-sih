// @vitest-environment jsdom
import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, expect, it } from "vitest";
import { VerificationCard } from "../app/components/DocumentAnalysis";
import type { DocumentT } from "../lib/types";

afterEach(cleanup);

it("keeps mismatch evidence visible and labels the simulated source", () => {
  const doc = { referenceNo: "DEMO-41", verification: { status: "MISMATCH_DETECTED", source: "Demo issuer (simulated)", comparisons: [{ field: "totalIntake", submitted: 9999, source: 300, match: false }] } } as DocumentT;
  render(<VerificationCard doc={doc} />);
  expect(screen.getAllByText("Demo issuer (simulated)").length).toBeGreaterThan(0);
  expect(screen.getByText("9,999")).toBeTruthy();
  expect(screen.getByText("300")).toBeTruthy();
  expect(screen.getByText("Verification evidence").closest("details")?.open).toBe(true);
});

it("does not describe an issuer outage as confirmed fraud", () => {
  const doc = { verification: { status: "SOURCE_UNAVAILABLE", source: "Demo issuer (simulated)" } } as DocumentT;
  render(<VerificationCard doc={doc} />);
  expect(screen.getByText(/not evidence of fraud/)).toBeTruthy();
  expect(screen.getByText("Verification evidence").closest("details")?.open).toBe(false);
});
