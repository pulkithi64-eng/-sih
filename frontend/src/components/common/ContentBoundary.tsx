import { Component, type ReactNode } from "react";
import { Button } from "@/components/ui/button";

/** Keep navigation available when a deferred section cannot be downloaded. */
export class ContentBoundary extends Component<{ children: ReactNode }, { failed: boolean }> {
  state = { failed: false };
  static getDerivedStateFromError() { return { failed: true }; }
  render() {
    if (this.state.failed) return <div role="alert" className="rounded-lg border bg-card p-6"><h2 className="font-semibold">This section could not load</h2><p className="mt-2 text-sm text-muted-foreground">Check your connection, then reload the page. Your saved application is unchanged.</p><Button className="mt-4" variant="outline" onClick={() => window.location.reload()}>Reload page</Button></div>;
    return this.props.children;
  }
}
