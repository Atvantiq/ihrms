import { AuthGate } from "@/components/AuthGate";

export default function ExitLayout({ children }: { children: React.ReactNode }) {
  return <AuthGate>{children}</AuthGate>;
}
