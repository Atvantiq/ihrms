import { AuthGate } from "@/components/AuthGate";

export default function TasksLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return <AuthGate>{children}</AuthGate>;
}
