import { useState } from 'react'

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

// The exact order the model was trained on (its feature_names_in_).
// /api/predict/ takes a plain list, so this order must never change.
const COURSES = [
  'Algorithms',
  'Computer Networks 1',
  'Data Communication',
  'Data Structures',
  'Database System 1',
  'Discrete Structures',
  'Electronics 1',
  'English 1',
  'English 2',
  'Fundamentals of Information Systems',
  'Human Rights',
  'Internet Technology',
  'Intro to Computers',
  'Logic Design',
  'Maths 1',
  'Maths 2',
  'Operating Systems 1',
  'Operations Research',
  'Physics',
  'Probability & Statistics 1',
  'Programming 1',
  'Programming 2',
  'Software Engineering 1',
  'System Analysis & Design 1',
]

function SpecializationWidget() {
  const [open, setOpen] = useState(false)
  const [grades, setGrades] = useState<string[]>(() => COURSES.map(() => ''))
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [result, setResult] = useState('')

  function updateGrade(index: number, value: string) {
    setGrades((prev) => prev.map((g, i) => (i === index ? value : g)))
  }

  async function handleSubmit() {
    setError('')

    const numbers = grades.map((g) => (g.trim() === '' ? NaN : Number(g)))
    if (numbers.some((n) => Number.isNaN(n) || n < 0 || n > 100)) {
      setError('من فضلك أدخلي الـ 24 درجة كلها، وكل درجة بين 0 و100.')
      return
    }

    setLoading(true)
    try {
      const token = localStorage.getItem('token')
      const res = await fetch(`${API_BASE}/api/predict/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({ grades: numbers }),
      })

      if (res.status === 401) {
        localStorage.removeItem('token')
        window.location.href = '/login'
        return
      }

      const data = await res.json().catch(() => ({}))

      if (!res.ok) {
        setError(data.error || 'تعذّر الحصول على التوصية، حاولي تاني.')
        return
      }

      setResult(data.predicted_department)
      setOpen(false)
    } catch {
      setError('تعذّر الاتصال بالسيرفر، اتأكدي إنه شغّال.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="card span12">
      <h3><span className="icon">🧭</span> التخصص المناسب ليكي (توصية بالذكاء الاصطناعي)</h3>

      {result && !open && (
        <div className="recoResult">
          <div className="recoLabel">التخصص المقترح</div>
          <div className="recoValue">{result}</div>
          <div className="recoNote">التوصية مبنية على الدرجات اللي دخلتيها.</div>
        </div>
      )}

      {!open ? (
        <button type="button" className="recoBtn" onClick={() => setOpen(true)}>
          {result ? 'جرّبي بدرجات تانية' : 'اعرفي التخصص المناسب'}
        </button>
      ) : (
        <>
          <p className="recoHint">أدخلي درجتك (من 100) في كل مادة من المواد دي.</p>
          <div className="recoGrid">
            {COURSES.map((name, i) => (
              <label className="recoField" key={name}>
                <span dir="ltr">{name}</span>
                <input
                  type="number"
                  min={0}
                  max={100}
                  step="any"
                  inputMode="decimal"
                  value={grades[i]}
                  onChange={(e) => updateGrade(i, e.target.value)}
                />
              </label>
            ))}
          </div>
          {error && <div className="recoError">{error}</div>}
          <button type="button" className="recoBtn" onClick={handleSubmit} disabled={loading}>
            {loading ? 'جاري التحليل...' : 'احسبي التوصية'}
          </button>
        </>
      )}
    </div>
  )
}

export default SpecializationWidget