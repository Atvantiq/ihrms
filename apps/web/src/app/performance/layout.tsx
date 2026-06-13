import { AuthGate } from "@/components/AuthGate";

export default function PerformanceLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return <AuthGate>{children}</AuthGate>;
}
