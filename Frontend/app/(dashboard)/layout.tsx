import { DashboardLayout } from '@/components/dashboard-layout'

export default function AuthenticatedProductLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return <DashboardLayout>{children}</DashboardLayout>
}
