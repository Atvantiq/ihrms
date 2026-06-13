import { AuthGate } from "@/components/AuthGate";

export default function BandsLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return <AuthGate>{children}</AuthGate>;
}
