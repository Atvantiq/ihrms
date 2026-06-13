import { AuthGate } from "@/components/AuthGate";

export default function FeedbackLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return <AuthGate>{children}</AuthGate>;
}
