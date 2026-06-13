import { AuthGate } from "@/components/AuthGate";

export default function TaxLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return <AuthGate>{children}</AuthGate>;
}
