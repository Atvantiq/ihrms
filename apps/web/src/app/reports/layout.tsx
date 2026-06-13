import { AuthGate } from "@/components/AuthGate";

export default function ReportsLayout({ children }: { children: React.ReactNode }) {
  return <AuthGate>{children}</AuthGate>;
}
