import { AuthGate } from "@/components/AuthGate";

export default function DirectoryLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return <AuthGate>{children}</AuthGate>;
}
