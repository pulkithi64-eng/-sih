import { describe, expect, it } from "vitest";
import { applicationStage, institutionNextAction, verificationNextStep } from "../lib/journey";
import { homePathFor } from "../app/auth";
import { NAV_SECTIONS } from "../app/layout/nav";
import type { Application, ApplicationStatus, Role } from "../lib/types";

const application = (status: ApplicationStatus, documents = 0) => ({ id: 41, status, counts: { documents } }) as Application;

describe("role entry points and institution next steps", () => {
  it("takes each role directly to its core workflow", () => {
    expect(homePathFor("INSTITUTION")).toBe("/portal/my-applications");
    expect(homePathFor("SCRUTINY_OFFICER")).toBe("/portal/applications");
    expect(homePathFor("REGIONAL_DIRECTOR")).toBe("/portal/applications?status=RECOMMENDED");
    expect(homePathFor("ADMIN")).toBe("/portal/rules");
  });
  it("makes draft upload a bookmarkable action for empty and existing drafts", () => {
    for (const count of [0, 2]) expect(institutionNextAction(application("DRAFT", count))).toMatchObject({ label: "Upload documents", to: "/portal/applications/41/edit?step=documents" });
  });
  it("sends corrections to the response step and locks submitted cases to progress", () => {
    for (const status of ["RECTIFICATION_REQUESTED", "DEFICIENCIES_FLAGGED"] as const) expect(institutionNextAction(application(status)).to).toContain("?step=respond");
    for (const status of ["SUBMITTED", "UNDER_REVIEW", "DECIDED"] as const) expect(institutionNextAction(application(status)).to).toBe("/portal/applications/41");
  });
  it("shows progress without presenting a draft as reviewed", () => {
    expect(applicationStage(application("DRAFT"))).toBe(0);
    expect(applicationStage(application("DRAFT", 1))).toBe(1);
    expect(applicationStage(application("UNDER_REVIEW"))).toBe(2);
    expect(applicationStage(application("RECOMMENDED"))).toBe(3);
    expect(applicationStage(application("DECIDED"))).toBe(4);
  });
  it("does not offer the institution an administrative workspace", () => {
    const visible = (role: Role) => NAV_SECTIONS.flatMap(section => section.items.filter(item => item.roles.includes(role)));
    expect(visible("INSTITUTION").some(item => ["/portal/rules", "/portal/sources", "/portal/audit"].includes(item.to))).toBe(false);
    expect(visible("ADMIN").some(item => item.to === "/portal/applications/new")).toBe(false);
  });
  it("preserves uncertainty and human authority in document guidance", () => {
    expect(verificationNextStep("SOURCE_UNAVAILABLE")).toContain("not evidence of fraud");
    expect(verificationNextStep("VERIFIED")).toContain("does not approve");
    expect(verificationNextStep("MANUAL_REVIEW_REQUIRED")).toContain("reviewer");
    expect(verificationNextStep("UNKNOWN")).toContain("reviewer");
  });
});
