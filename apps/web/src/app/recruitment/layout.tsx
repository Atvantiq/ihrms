import { AuthGate } from "@/components/AuthGate";

export default function RecruitmentLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return <AuthGate>{children}</AuthGate>;
}
