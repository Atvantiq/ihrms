import { AuthGate } from "@/components/AuthGate";

export default function ControlPlaneLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return <AuthGate>{children}</AuthGate>;
}
