import { AuthGate } from "@/components/AuthGate";

export default function ShiftsLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return <AuthGate>{children}</AuthGate>;
}
