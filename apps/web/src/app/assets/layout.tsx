import { AuthGate } from "@/components/AuthGate";

export default function AssetsLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return <AuthGate>{children}</AuthGate>;
}
