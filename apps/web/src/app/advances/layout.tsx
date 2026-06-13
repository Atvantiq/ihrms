import { AuthGate } from "@/components/AuthGate";

export default function AdvancesLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return <AuthGate>{children}</AuthGate>;
}
