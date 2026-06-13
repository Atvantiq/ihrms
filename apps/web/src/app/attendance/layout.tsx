import { AuthGate } from "@/components/AuthGate";

export default function AttendanceLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return <AuthGate>{children}</AuthGate>;
}
