import { AuthGate } from "@/components/AuthGate";

export default function HelpdeskLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return <AuthGate>{children}</AuthGate>;
}
