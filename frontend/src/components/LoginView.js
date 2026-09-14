import React, {useState} from 'react';
import civLogo from '../assets/logociv.png';
import campusImage from '../assets/54088665669_251d9c0f8a_z.jpg';
import {useLanguage} from '../translations';

const ROLE_IDS = [
  'aspirante',
  'alumno',
  'coordinacion',
  'docente',
  'director',
  'admin',
];

export default function LoginView({onBackHome, onLoginSuccess}){
  const {t} = useLanguage();
  const [role, setRole] = useState('aspirante');
  const [usuario, setUsuario] = useState('');
  const [password, setPassword] = useState('');
  const [remember, setRemember] = useState(true);
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const getRoleLabel = (roleId) => {
    const key = `role.${roleId}`;
    return t(key);
  };
  const detectedRoleLabel = getRoleLabel(role);

  function validate(){
    if (!usuario.trim() || !password.trim()) {
      setError(t('login.errorValidation'));
      return false;
    }
    setError('');
    return true;
  }

  async function handleSubmit(e){
    e.preventDefault();
    if (!validate()) return;
    setLoading(true);

    const normalizedUsuario = usuario.trim();

    try {
      const res = await fetch('/api/auth/login/', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({usuario: normalizedUsuario, password}),
      });
      const data = await res.json();
      if (!res.ok) {
        setError(data.detail || t('login.errorCredentials'));
        setLoading(false);
        return;
      }

      const rawRole = data.role ?? data.rol ?? role ?? 'aspirante';
      const authenticatedRole = String(rawRole).trim() || 'aspirante';
      setRole(authenticatedRole);

      const storage = remember ? localStorage : sessionStorage;
      storage.setItem('sinac_access', data.access);
      storage.setItem('sinac_refresh', data.refresh);
      storage.setItem('sinac_role', authenticatedRole);

      if (typeof onLoginSuccess === 'function') {
        onLoginSuccess({role: authenticatedRole, access: data.access, refresh: data.refresh});
      }
    } catch {
      setError(t('login.errorConnection'));
    }
    setLoading(false);
  }

  return (
    <section id="login" className="login-section single-panel-login">
      <div className="login-layout-modern">
        <div className="login-visual" aria-label="Campus Cinvestav Zacatenco">
          <img src={campusImage} alt="Campus Cinvestav Zacatenco" />
          <div className="login-visual-caption"><span>CINVESTAV</span><strong>Unidad Zacatenco</strong><small>Investigación · Ciencia · Tecnología</small></div>
        </div>
      <div className="login-card modern-login-card single-panel-card">
        <div className="login-branding">
          <div className="login-logo-wrap">
            <img src={civLogo} alt="CINVESTAV" className="login-civ-logo" />
          </div>
          <div className="login-badge">{t('login.institutionalAccess')}</div>
        </div>

        <div className="login-brand-copy">
          <h1>{t('login.systemName')}</h1>
          <p>{t('login.description')}</p>
        </div>

        <div className="login-header">
          <p className="login-kicker">{t('login.welcome')}</p>
          <h2>{t('login.signIn')}</h2>
        </div>

        <form className="login-form" onSubmit={handleSubmit} noValidate>
          <label>
            {t('login.userOrEmail')}
            <input
              type="text"
              placeholder={t('login.userPlaceholder')}
              value={usuario}
              onChange={(e) => setUsuario(e.target.value)}
            />
          </label>

          <label>
            {t('login.password')}
            <div className="password-row">
              <input
                type={showPassword ? 'text' : 'password'}
                placeholder={t('login.passwordPlaceholder')}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />
              <button
                type="button"
                className="toggle-password"
                onClick={() => setShowPassword(v => !v)}
                aria-label={showPassword ? t('login.password') : t('login.password')}
              >
                {showPassword ? 'Ocultar' : 'Mostrar'}
              </button>
            </div>
          </label>

          <div className="login-role-readonly">
            <span>Perfil detectado</span>
            <strong>{detectedRoleLabel}</strong>
          </div>

          <div className="login-row">
            <label className="remember-check">
              <input
                type="checkbox"
                checked={remember}
                onChange={(e) => setRemember(e.target.checked)}
              />
              {t('login.rememberMe')}
            </label>
            <button type="button" className="link-btn">{t('login.forgotPassword')}</button>
          </div>

          {error ? <div className="login-error">{error}</div> : null}

          <button type="submit" className="login-submit" disabled={loading}>
            {loading ? t('login.signIn') + '...' : t('login.signInButton')}
          </button>

          <button type="button" className="login-back login-back-inline" onClick={onBackHome}>
            {t('navbar.home')}
          </button>
        </form>
      </div>
      </div>
    </section>
  );
}
