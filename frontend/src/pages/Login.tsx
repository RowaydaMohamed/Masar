import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import './Login.css'

type IdMode = 'id' | 'email'

function Login() {
  const navigate = useNavigate()

  const [mode, setMode] = useState<IdMode>('id')
  const [idValue, setIdValue] = useState('')
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [capsOn, setCapsOn] = useState(false)
  const [rememberMe, setRememberMe] = useState(false)
  const [errorMsg, setErrorMsg] = useState('')
  const [idError, setIdError] = useState(false)
  const [passError, setPassError] = useState(false)
  const [loading, setLoading] = useState(false)

  function handleModeChange(newMode: IdMode) {
    setMode(newMode)
    setIdValue('')
    setIdError(false)
  }

  function handlePasswordKeyUp(e: React.KeyboardEvent<HTMLInputElement>) {
    setCapsOn(e.getModifierState && e.getModifierState('CapsLock'))
  }

  function handleForgotPassword(e: React.MouseEvent) {
    e.preventDefault()
    setErrorMsg('استعادة كلمة المرور هتتحط في صفحة منفصلة لاحقًا — دي شاشة تسجيل الدخول بس دلوقتي.')
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setErrorMsg('')
    setIdError(false)
    setPassError(false)

    let valid = true
    if (!idValue.trim()) {
      setIdError(true)
      valid = false
    }
    if (!password.trim()) {
      setPassError(true)
      valid = false
    }
    if (!valid) {
      setErrorMsg('من فضلك أكملي البيانات المطلوبة.')
      return
    }

    setLoading(true)
    // simulated auth delay — this stage is UI-only; real check happens once
    // the backend/auth endpoint exists
    setTimeout(() => {
      navigate('/dashboard')
    }, 850)
  }

  return (
    <div className="loginPage">
      {/* ============ LEFT — decorative brand panel ============ */}
      <aside className="brandPane">
        <div className="brandTop">
          <div className="logo">م<span>سار</span></div>
          <div className="tag">نظام تخطيط التسجيل والتخرج — كلية الحاسبات والذكاء الاصطناعي، جامعة حلوان</div>
        </div>

        <div className="treeArt">
          <svg viewBox="0 0 420 300" xmlns="http://www.w3.org/2000/svg">
            <defs>
              <marker id="ah" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
                <path d="M0,0 L10,5 L0,10 z" fill="#7C8CB0" />
              </marker>
            </defs>
            <g stroke="#7C8CB0" strokeWidth="1.2" fill="none" opacity="0.75">
              <path d="M210,30 C210,55 210,55 130,80" markerEnd="url(#ah)" />
              <path d="M210,30 C210,55 210,55 290,80" markerEnd="url(#ah)" />
              <path d="M130,80 C130,105 130,105 90,130" markerEnd="url(#ah)" />
              <path d="M130,80 C130,105 130,105 170,130" markerEnd="url(#ah)" />
              <path d="M290,80 C290,105 290,105 250,130" markerEnd="url(#ah)" />
              <path d="M290,80 C290,105 290,105 330,130" markerEnd="url(#ah)" />
              <path d="M90,130 C90,155 90,155 90,180" markerEnd="url(#ah)" />
              <path d="M170,130 C170,155 170,155 210,180" markerEnd="url(#ah)" />
              <path d="M250,130 C250,155 250,155 210,180" markerEnd="url(#ah)" />
              <path d="M330,130 C330,155 330,155 330,180" markerEnd="url(#ah)" />
              <path d="M210,180 C210,205 210,205 210,230" markerEnd="url(#ah)" />
            </g>
            <g fontFamily="IBM Plex Mono" fontSize="10" fill="#16233F" textAnchor="middle">
              <g><ellipse cx="210" cy="20" rx="46" ry="18" fill="#E9CE87" /><text x="210" y="24">CS111</text></g>
              <g><ellipse cx="130" cy="80" rx="42" ry="17" fill="#D9E2F2" /><text x="130" y="84">CS112</text></g>
              <g><ellipse cx="290" cy="80" rx="42" ry="17" fill="#D9E2F2" /><text x="290" y="84">MA111</text></g>
              <g><ellipse cx="90" cy="130" rx="42" ry="17" fill="#D9E2F2" /><text x="90" y="134">CS214</text></g>
              <g><ellipse cx="170" cy="130" rx="42" ry="17" fill="#D9E2F2" /><text x="170" y="134">CS221</text></g>
              <g><ellipse cx="250" cy="130" rx="42" ry="17" fill="#D9E2F2" /><text x="250" y="134">MA113</text></g>
              <g><ellipse cx="330" cy="130" rx="42" ry="17" fill="#D9E2F2" /><text x="330" y="134">ST121</text></g>
              <g><ellipse cx="90" cy="180" rx="42" ry="17" fill="#C9DCEF" /><text x="90" y="184">CS316</text></g>
              <g><ellipse cx="210" cy="180" rx="46" ry="17" fill="#C9DCEF" /><text x="210" y="184">AI330</text></g>
              <g><ellipse cx="330" cy="180" rx="42" ry="17" fill="#C9DCEF" /><text x="330" y="184">IT221</text></g>
              <g><ellipse cx="210" cy="230" rx="50" ry="19" fill="#E9CE87" /><text x="210" y="234">AI310</text></g>
            </g>
          </svg>
        </div>

        <div className="brandBottom">
          <div className="quote">"اعرف <span>مسارك</span> قبل ما تسجّل — مش بعد ما تتعثر فيه."</div>
          <div className="sub">مشروع تخرج — قسم الذكاء الاصطناعي · فرقة رابعة</div>
        </div>
      </aside>

      {/* ============ Login form ============ */}
      <main className="formPane">
        <div className="formCard">
          <h1>تسجيل دخول الطالب</h1>
          <p className="lead">ادخلي ببيانات حسابك الجامعي لتشوفي خطتك الدراسية.</p>

          <div className="segToggle">
            <button type="button" className={mode === 'id' ? 'active' : ''} onClick={() => handleModeChange('id')}>
              الرقم الجامعي
            </button>
            <button type="button" className={mode === 'email' ? 'active' : ''} onClick={() => handleModeChange('email')}>
              البريد الجامعي
            </button>
          </div>

          {errorMsg && (
            <div className="errorBanner show">
              <span>⚠️</span><span>{errorMsg}</span>
            </div>
          )}

          <form onSubmit={handleSubmit} noValidate>
            <div className="field">
              <label htmlFor="idInput">{mode === 'email' ? 'البريد الجامعي' : 'الرقم الجامعي'}</label>
              <div className="inputWrap">
                <input
                  type={mode === 'email' ? 'email' : 'text'}
                  id="idInput"
                  placeholder={mode === 'email' ? 'مثال: name@fci.helwan.edu.eg' : 'مثال: 2021170045'}
                  autoComplete="username"
                  className={idError ? 'errorField' : ''}
                  value={idValue}
                  onChange={(e) => { setIdValue(e.target.value); setIdError(false) }}
                />
                {mode === 'email' ? (
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
                    <path d="M3 6h18v12H3z" /><path d="M3 6l9 7 9-7" />
                  </svg>
                ) : (
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
                    <rect x="3" y="5" width="18" height="14" rx="2" /><path d="M3 9h18" /><path d="M7 13h4" />
                  </svg>
                )}
              </div>
            </div>

            <div className="field">
              <label htmlFor="passInput">كلمة المرور</label>
              <div className="inputWrap">
                <input
                  type={showPassword ? 'text' : 'password'}
                  id="passInput"
                  placeholder="••••••••"
                  autoComplete="current-password"
                  className={passError ? 'errorField' : ''}
                  value={password}
                  onChange={(e) => { setPassword(e.target.value); setPassError(false) }}
                  onKeyUp={handlePasswordKeyUp}
                />
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
                  <rect x="4" y="10" width="16" height="10" rx="2" /><path d="M8 10V7a4 4 0 0 1 8 0v3" />
                </svg>
                <button type="button" className="toggleEye" title="إظهار/إخفاء كلمة المرور" onClick={() => setShowPassword(!showPassword)}>
                  <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
                    <path d="M1 12s4-7 11-7 11 7 11 7-4 7-11 7-11-7-11-7z" /><circle cx="12" cy="12" r="3" />
                  </svg>
                </button>
              </div>
              {capsOn && <div className="capsWarn show">🔺 مفتاح Caps Lock مفعّل</div>}
            </div>

            <div className="rowBetween">
              <label className="rememberMe">
                <input type="checkbox" checked={rememberMe} onChange={(e) => setRememberMe(e.target.checked)} /> تذكرني
              </label>
              <a href="#" className="forgotLink" onClick={handleForgotPassword}>نسيت كلمة المرور؟</a>
            </div>

            <button type="submit" className="submitBtn" disabled={loading}>
              {loading && <span className="spinner show" />}
              <span>{loading ? 'جاري التحقق...' : 'تسجيل الدخول'}</span>
            </button>
          </form>

          <div className="helpNote">
            لسه معملتش تفعيل لحسابك؟ <b>تواصل مع شؤون الطلاب</b> لتفعيل حساب النظام ببيانات جامعتك.
          </div>
        </div>
      </main>
    </div>
  )
}

export default Login