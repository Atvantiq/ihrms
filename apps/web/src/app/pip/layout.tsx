import { AuthGate } from "@/components/AuthGate";

export default function PipLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return <AuthGate>{children}</AuthGate>;
}
