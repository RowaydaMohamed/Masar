import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import './Dashboard.css'

// ============ Shape of the data we expect from Mahmoud's real API ============
// Keeping this typed now means swapping mock -> real fetch later is a 1-line change.
interface DashboardData {
  student: {
    name: string
    avatarLetter: string
    major: string
    year: string
    cgpa: number
  }
  stats: {
    completedHours: number
    totalHours: number
    progressPercent: number
    currentCourses: number
    remainingHours: number
  }
  registeredCourses: { code: string; name: string; hours: number }[]
  schedule: {
    time: string
    slots: (null | { code: string; variant?: 'alt' | 'alt2' })[]
  }[]
  deadline: { daysLeft: number; dateLabel: string }
  summerRequests: { name: string; status: 'approved' | 'pending' | 'rejected' | 'review'; statusLabel: string }[]
  seventhCourseRequest: { code: string; name: string; statusLabel: string; note: string }
  notifications: { icon: string; text: string; time: string }[]
}

// ============ TEMPORARY mock data — matches the shape above ============
// TODO: once Mahmoud's GET /api/dashboard endpoint is ready, delete this
// and use the real fetch call in useEffect below instead.
const MOCK_DATA: DashboardData = {
  student: { name: 'يمنى أحمد', avatarLetter: 'ي', major: 'هندسة البرمجيات', year: 'الفرقة الرابعة', cgpa: 3.53 },
  stats: { completedHours: 108, totalHours: 132, progressPercent: 82, currentCourses: 6, remainingHours: 24 },
  registeredCourses: [
    { code: 'AI330', name: 'تعلم الآلة', hours: 3 },
    { code: 'IT441', name: 'معالجة الصور 1', hours: 3 },
    { code: 'AI430', name: 'الذكاء الحاسوبي', hours: 3 },
    { code: 'HU313', name: 'حقوق الإنسان', hours: 2 },
    { code: 'IS231', name: 'أساسيات نظم المعلومات', hours: 3 },
    { code: 'AI498', name: 'مشروع التخرج', hours: 6 },
  ],
  schedule: [
    { time: '9:00–11:00', slots: [{ code: 'AI330' }, null, { code: 'AI330' }, null, { code: 'IS231', variant: 'alt2' }] },
    { time: '11:00–1:00', slots: [null, { code: 'IT441', variant: 'alt' }, null, { code: 'IT441', variant: 'alt' }, null] },
    { time: '1:00–3:00', slots: [{ code: 'AI430', variant: 'alt2' }, null, { code: 'AI430', variant: 'alt2' }, null, { code: 'HU313' }] },
  ],
  deadline: { daysLeft: 3, dateLabel: 'آخر موعد: الخميس القادم — 11:59 م' },
  summerRequests: [
    { name: 'ST122 — إحصاء 2', status: 'approved', statusLabel: 'هتُفتح' },
    { name: 'CS241 — نظم تشغيل 1', status: 'review', statusLabel: 'قيد المراجعة' },
    { name: 'IT222 — شبكات حاسب 1', status: 'pending', statusLabel: 'طلب مُرسَل' },
  ],
  seventhCourseRequest: {
    code: 'IS351',
    name: 'تحليل وتصميم نظم المعلومات 1',
    statusLabel: 'قيد المراجعة',
    note: 'اتبعت بناءً على معدلك (3.53) — الإدارة هتراجعه خلال يومين غالبًا',
  },
  notifications: [
    { icon: '✅', text: 'تم قبول طلب تسجيلك في <b>ST122 — إحصاء 2</b> (تسجيل صيفي)', time: 'من يومين' },
    { icon: '⏳', text: 'طلب المادة السابعة (<b>IS351</b>) لسه قيد المراجعة من الإدارة', time: 'من 3 أيام' },
    { icon: '📅', text: 'باب التسجيل هيقفل خلال <b>3 أيام</b> — راجعي جدولك قبل الموعد', time: 'النهاردة' },
    { icon: '🟡', text: 'أداءك في <b>AI330</b> لسه تحت المتوسط — يفضّل تراجعي المادة بدري', time: 'من أسبوع' },
  ],
}

const DAYS = ['الأحد', 'الاثنين', 'الثلاثاء', 'الأربعاء', 'الخميس']

function Dashboard() {
  const navigate = useNavigate()
  const [data, setData] = useState<DashboardData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    // ---- TEMPORARY: simulate a network request with mock data ----
    // TODO: replace this whole block with:
    //   const token = localStorage.getItem('token')
    //   const res = await fetch('http://localhost:8000/api/dashboard', {
    //     headers: { Authorization: `Bearer ${token}` }
    //   })
    //   if (res.ok) setData(await res.json())
    //   else setError('حصل خطأ في تحميل البيانات')
    const timer = setTimeout(() => {
      setData(MOCK_DATA)
      setLoading(false)
    }, 600)
    return () => clearTimeout(timer)
  }, [])

  function handleLogout() {
    localStorage.removeItem('token')
    navigate('/login')
  }

  if (loading) {
    return (
      <div className="dashboardPage">
        <div className="stateBox">جاري التحميل...</div>
      </div>
    )
  }

  if (error || !data) {
    return (
      <div className="dashboardPage">
        <div className="stateBox errorState">{error || 'حصل خطأ غير متوقع'}</div>
      </div>
    )
  }

  const ringCircumference = 263.9
  const ringOffset = ringCircumference - (ringCircumference * data.stats.progressPercent) / 100

  return (
    <div className="dashboardPage">
      <header className="nav">
        <div className="navInner">
          <div className="navBrand">م<span>سار</span></div>
          <nav className="navLinks">
            <Link to="/dashboard" className="active">لوحة التحكم</Link>
            <Link to="/curriculum-tree">شجرتي</Link>
            <Link to="/explore">استكشاف التخصصات</Link>
            <Link to="/graduation-tracker">مسار التخرج</Link>
          </nav>
          <div className="navUser">
            <div className="avatar">{data.student.avatarLetter}</div>
            <span className="uname">{data.student.name}</span>
            <button className="logoutBtn" onClick={handleLogout}>تسجيل الخروج</button>
          </div>
        </div>
      </header>

      <div className="wrap">
        <section className="hero">
          <h1>أهلًا، {data.student.name.split(' ')[0]} 👋</h1>
          <div className="subline">
            <span className="pill">🎓 {data.student.major}</span>
            <span className="pill">{data.student.year}</span>
            <span className="pill">CGPA: {data.student.cgpa}</span>
          </div>
          <div className="statRow">
            <div className="statChip">
              <div className="lbl">الساعات المكتملة</div>
              <div className="val">{data.stats.completedHours}<small> / {data.stats.totalHours}</small></div>
              <div className="miniBar"><div className="fill" style={{ width: `${data.stats.progressPercent}%` }} /></div>
            </div>
            <div className="statChip">
              <div className="lbl">نسبة التقدّم للتخرج</div>
              <div className="val">{data.stats.progressPercent}%</div>
            </div>
            <div className="statChip">
              <div className="lbl">المواد المسجَّلة حاليًا</div>
              <div className="val">{data.stats.currentCourses}</div>
            </div>
            <div className="statChip">
              <div className="lbl">الساعات المتبقية</div>
              <div className="val">{data.stats.remainingHours}</div>
            </div>
            <div className="statChip">
              <div className="lbl">المعدل التراكمي</div>
              <div className="val">{data.student.cgpa}</div>
            </div>
          </div>
        </section>

        <div className="grid">
          <div className="card span5">
            <h3><span className="icon">🎓</span> التقدّم في اللائحة</h3>
            <div className="ringWrap">
              <svg width="100" height="100" viewBox="0 0 100 100">
                <circle cx="50" cy="50" r="42" fill="none" stroke="var(--grey-soft)" strokeWidth="10" />
                <circle
                  cx="50" cy="50" r="42" fill="none" stroke="var(--gold-deep)" strokeWidth="10"
                  strokeLinecap="round" strokeDasharray={ringCircumference} strokeDashoffset={ringOffset}
                  transform="rotate(-90 50 50)"
                />
                <text x="50" y="56" textAnchor="middle" className="ringLabel">{data.stats.progressPercent}%</text>
              </svg>
              <div>
                <div style={{ fontFamily: 'Cairo', fontWeight: 700, fontSize: 14 }}>
                  {data.stats.completedHours} من {data.stats.totalHours} ساعة معتمدة
                </div>
                <div className="ringSub">باقي {data.stats.remainingHours} ساعة للتخرج</div>
                <Link to="/curriculum-tree" className="ringLink">افتح الشجرة الكاملة ←</Link>
              </div>
            </div>
          </div>

          <div className="card span7">
            <h3><span className="icon">📚</span> المواد المسجَّلة هذا الفصل ({data.registeredCourses.length})</h3>
            {data.registeredCourses.map((c) => (
              <div className="courseRow" key={c.code}>
                <span className="cname">{c.code} — {c.name}</span>
                <span className="chours">{c.hours} ساعات <span className="tag-sm">مسجّلة</span></span>
              </div>
            ))}
          </div>

          <div className="card span12">
            <h3><span className="icon">📅</span> الجدول الحالي</h3>
            <table className="schedule">
              <thead>
                <tr>
                  <th></th>
                  {DAYS.map((d) => <th key={d}>{d}</th>)}
                </tr>
              </thead>
              <tbody>
                {data.schedule.map((row) => (
                  <tr key={row.time}>
                    <th>{row.time}</th>
                    {row.slots.map((slot, i) => (
                      <td key={i}>
                        {slot && <div className={`slotBlock ${slot.variant ?? ''}`}>{slot.code}</div>}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="card span4">
            <h3><span className="icon">⏳</span> معاد التسجيل القادم</h3>
            <div className="deadlineBig">{data.deadline.daysLeft} أيام</div>
            <div className="deadlineSub">متبقية على قفل تعديل التسجيل</div>
            <div className="deadlineDate">{data.deadline.dateLabel}</div>
          </div>

          <div className="card span4">
            <h3><span className="icon">☀️</span> طلبات الصيفي</h3>
            {data.summerRequests.map((r) => (
              <div className="summerItem" key={r.name}>
                <span>{r.name}</span>
                <span className={`badge ${r.status}`}>{r.statusLabel}</span>
              </div>
            ))}
          </div>

          <div className="card span4">
            <h3><span className="icon">➕</span> طلب المادة السابعة</h3>
            <div className="statusCourse">
              <div className="code">{data.seventhCourseRequest.code}</div>
              <div className="name">{data.seventhCourseRequest.name}</div>
              <span className="badge pending">{data.seventhCourseRequest.statusLabel}</span>
              <div style={{ fontSize: 11, color: 'var(--ink-soft)', marginTop: 10 }}>
                {data.seventhCourseRequest.note}
              </div>
            </div>
          </div>

          <div className="card span12">
            <h3><span className="icon">📢</span> آخر الإشعارات</h3>
            {data.notifications.map((n, i) => (
              <div className="notifRow" key={i}>
                <span className="nIcon">{n.icon}</span>
                <div>
                  <div className="nText" dangerouslySetInnerHTML={{ __html: n.text }} />
                  <div className="nTime">{n.time}</div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}

export default Dashboard