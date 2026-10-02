// ============ Types matching the real API response (Mahmoud's shape) ============
interface RawProfile {
  full_name: string
  specialization: string
  academic_level: number
  cgpa: number
  completed_hours: number
  required_hours: number
  graduation_progress_pct: number
  registered_count: number
}
interface RawCourse { code: string; name: string; hours: number }
interface RawScheduleItem { day: string; start: string; end: string; course_code: string }
interface RawSummerRequest { course_code: string; course_name: string; status: string }
interface RawSeventhCourseRequest { course_code: string; course_name: string; status: string }
interface RawNotification { icon: string; text: string; time: string }

interface RawDashboardResponse {
  profile: RawProfile
  registered_courses: RawCourse[]
  schedule: RawScheduleItem[]
  registration_deadline: string
  summer_requests: RawSummerRequest[]
  seventh_course_request: RawSeventhCourseRequest
  notifications: RawNotification[]
}

// ============ Shape our Dashboard.tsx already renders (unchanged) ============
export interface DashboardData {
  student: { name: string; avatarLetter: string; major: string; year: string; cgpa: number }
  stats: { completedHours: number; totalHours: number; progressPercent: number; currentCourses: number; remainingHours: number }
  registeredCourses: { code: string; name: string; hours: number }[]
  schedule: { time: string; slots: (null | { code: string; variant?: 'alt' | 'alt2' })[] }[]
  deadline: { daysLeft: number; dateLabel: string }
  summerRequests: { name: string; status: 'approved' | 'pending' | 'rejected' | 'review'; statusLabel: string }[]
  seventhCourseRequest: { code: string; name: string; statusLabel: string; note: string }
  notifications: { icon: string; text: string; time: string }[]
}

// ============ Your teammate's helper, converts an ISO date to "من X أيام" ============
function timeAgo(isoString: string): string {
  const diffMs = new Date().getTime() - new Date(isoString).getTime()
  const minutes = Math.floor(diffMs / 60000)
  const hours = Math.floor(minutes / 60)
  const days = Math.floor(hours / 24)

  if (days >= 1) return `من ${days} ${days === 1 ? 'يوم' : 'أيام'}`
  if (hours >= 1) return `من ${hours} ${hours === 1 ? 'ساعة' : 'ساعات'}`
  if (minutes >= 1) return `من ${minutes} دقيقة`
  return 'الآن'
}

const YEAR_LABELS: Record<number, string> = {
  1: 'الفرقة الأولى',
  2: 'الفرقة الثانية',
  3: 'الفرقة الثالثة',
  4: 'الفرقة الرابعة',
  5: 'فرقة خامسة / امتياز',
}

const STATUS_LABELS: Record<string, string> = {
  approved: 'هتُفتح',
  pending: 'طلب مُرسَل',
  rejected: 'مرفوض',
  review: 'قيد المراجعة',
}

const DAYS_ORDER = ['الأحد', 'الاثنين', 'الثلاثاء', 'الأربعاء', 'الخميس']

function buildScheduleGrid(raw: RawScheduleItem[]): DashboardData['schedule'] {
  const timeKeys = Array.from(new Set(raw.map((i) => `${i.start}-${i.end}`))).sort()
  return timeKeys.map((key) => {
    const [start, end] = key.split('-')
    const slots = DAYS_ORDER.map((day) => {
      const match = raw.find((i) => i.day === day && i.start === start && i.end === end)
      return match ? { code: match.course_code } : null
    })
    return { time: `${start}–${end}`, slots }
  })
}

function buildDeadline(iso: string): DashboardData['deadline'] {
  const deadlineDate = new Date(iso)
  const diffMs = deadlineDate.getTime() - new Date().getTime()
  const daysLeft = Math.max(0, Math.ceil(diffMs / 86400000))
  const dateLabel = `آخر موعد: ${deadlineDate.toLocaleDateString('ar-EG', {
    weekday: 'long', day: 'numeric', month: 'long',
  })} — ${deadlineDate.toLocaleTimeString('ar-EG', { hour: '2-digit', minute: '2-digit' })}`
  return { daysLeft, dateLabel }
}

// ============ The adapter: raw API shape -> what Dashboard.tsx expects ============
function mapToDashboardData(raw: RawDashboardResponse): DashboardData {
  const { profile } = raw
  return {
    student: {
      name: profile.full_name,
      avatarLetter: profile.full_name.trim().charAt(0),
      major: profile.specialization,
      year: YEAR_LABELS[profile.academic_level] ?? `الفرقة ${profile.academic_level}`,
      cgpa: profile.cgpa,
    },
    stats: {
      completedHours: profile.completed_hours,
      totalHours: profile.required_hours,
      progressPercent: profile.graduation_progress_pct,
      currentCourses: profile.registered_count,
      remainingHours: profile.required_hours - profile.completed_hours,
    },
    registeredCourses: raw.registered_courses,
    schedule: buildScheduleGrid(raw.schedule),
    deadline: buildDeadline(raw.registration_deadline),
    summerRequests: raw.summer_requests.map((r) => ({
      name: `${r.course_code} — ${r.course_name}`,
      status: (r.status as DashboardData['summerRequests'][number]['status']) ?? 'pending',
      statusLabel: STATUS_LABELS[r.status] ?? r.status,
    })),
    seventhCourseRequest: {
      code: raw.seventh_course_request.course_code,
      name: raw.seventh_course_request.course_name,
      statusLabel: STATUS_LABELS[raw.seventh_course_request.status] ?? raw.seventh_course_request.status,
      note: `بناءً على معدلك (${profile.cgpa}) — الإدارة هتراجع الطلب قريبًا`,
    },
    notifications: raw.notifications.map((n) => ({
      icon: n.icon,
      text: n.text,
      time: timeAgo(n.time),
    })),
  }
}

// ============ The real network call ============
const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

export async function fetchDashboard(): Promise<DashboardData> {
  const token = localStorage.getItem('token')

  const res = await fetch(`${API_BASE}/api/dashboard`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  })

  if (!res.ok) {
    throw new Error('تعذر تحميل بيانات لوحة التحكم')
  }

  const raw: RawDashboardResponse = await res.json()
  return mapToDashboardData(raw)
}