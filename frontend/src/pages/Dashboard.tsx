import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import './Dashboard.css'
import { fetchDashboard, type DashboardData } from '../lib/dashboardApi'
const DAYS = ['الأحد', 'الاثنين', 'الثلاثاء', 'الأربعاء', 'الخميس']

function Dashboard() {
  const navigate = useNavigate()
  const [data, setData] = useState<DashboardData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

     useEffect(() => {
    let cancelled = false
    fetchDashboard()
      .then((result) => {
        if (!cancelled) {
          setData(result)
          setLoading(false)
        }
      })
      .catch((err: Error) => {
        if (!cancelled) {
          setError(err.message || 'حصل خطأ غير متوقع')
          setLoading(false)
        }
      })
    return () => { cancelled = true }
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