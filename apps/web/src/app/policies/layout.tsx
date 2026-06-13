import { AuthGate } from "@/components/AuthGate";

export default function PoliciesLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return <AuthGate>{children}</AuthGate>;
}
