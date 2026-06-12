import { AuthGate } from "@/components/AuthGate";

export default function SettingsLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return <AuthGate>{children}</AuthGate>;
}
