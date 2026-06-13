import { AuthGate } from "@/components/AuthGate";

export default function LeaveLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return <AuthGate>{children}</AuthGate>;
}
