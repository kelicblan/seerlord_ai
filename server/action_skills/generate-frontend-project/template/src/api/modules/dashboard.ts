import { get } from '@/api/http'

export interface DashboardOverview {
  onlineModules: number
  draftModules: number
  totalModules: number
  lastReleaseAt: string
}

export const fetchDashboardOverviewApi = () => get<DashboardOverview>('/dashboard/overview')
