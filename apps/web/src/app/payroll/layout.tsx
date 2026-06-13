import { AuthGate } from "@/components/AuthGate";

export default function PayrollLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return <AuthGate>{children}</AuthGate>;
}
