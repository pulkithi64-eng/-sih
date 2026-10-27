import { Link } from "react-router-dom";
import { Compass } from "lucide-react";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/common/EmptyState";

export default function NotFoundPage() {
  return (
    <EmptyState
      icon={Compass}
      title="Page not found"
      description="The page you are looking for does not exist in the portal."
      action={
        <Button asChild size="sm">
          <Link to="/portal">Go to portal home</Link>
        </Button>
      }
    />
  );
}
