import { AuthGate } from "@/components/AuthGate";

export default function SelfServiceLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return <AuthGate>{children}</AuthGate>;
}
