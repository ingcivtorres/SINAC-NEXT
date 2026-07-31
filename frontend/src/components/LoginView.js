import React, {useState} from 'react';

export default function LoginView({onBackHome}){
  const [usuario, setUsuario] = useState('');
  const [password, setPassword] = useState('');
  const [remember, setRemember] = useState(true);
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  function validate(){
    if (!usuario.trim() || !password.trim()) {
      setError('Captura usuario/correo y contraseña.');
      return false;
    }
    if (usuario.includes('@') && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(usuario)) {
      setError('El correo no tiene un formato válido.');
      return false;
    }
    setError('');
    return true;
  }

  function handleSubmit(e){
    e.preventDefault();
    if (!validate()) return;

    setLoading(true);
    setTimeout(() => {
      setLoading(false);
      setError('Demo activa: autenticación backend pendiente de implementación.');
    }, 900);
  }

  return (
    <section id="login" className="login-section">
      <div className="login-layout">
        <aside className="login-side-card">
          <p className="login-kicker">Acceso Institucional</p>
          <h1>SINAC NEXT</h1>
          <p>
            Ingresa con tu cuenta de pre-registro para consultar el estado de tu solicitud,
            continuar capturas pendientes y dar seguimiento al flujo académico.
          </p>
          <ul>
            <li>Seguimiento del trámite por etapas.</li>
            <li>Actualización de datos del expediente.</li>
            <li>Trazabilidad de procesos LIDA/Camunda.</li>
          </ul>
          <button type="button" className="login-back" onClick={onBackHome}>Volver a Inicio</button>
        </aside>

        <div className="login-card">
          <div className="login-header">
            <h2>Iniciar sesión</h2>
            <p>Accede con tu usuario registrado en el pre-registro.</p>
          </div>

          <form className="login-form" onSubmit={handleSubmit} noValidate>
            <label>
              Usuario o correo
              <input
                type="text"
                placeholder="usuario@correo.com"
                value={usuario}
                onChange={(e)=>setUsuario(e.target.value)}
              />
            </label>

            <label>
              Contraseña
              <div className="password-row">
                <input
                  type={showPassword ? 'text' : 'password'}
                  placeholder="••••••••"
                  value={password}
                  onChange={(e)=>setPassword(e.target.value)}
                />
                <button
                  type="button"
                  className="toggle-password"
                  onClick={() => setShowPassword(v => !v)}
                  aria-label={showPassword ? 'Ocultar contraseña' : 'Mostrar contraseña'}
                >
                  {showPassword ? 'Ocultar' : 'Mostrar'}
                </button>
              </div>
            </label>

            <div className="login-row">
              <label className="remember-check">
                <input
                  type="checkbox"
                  checked={remember}
                  onChange={(e)=>setRemember(e.target.checked)}
                />
                Recordarme
              </label>
              <button type="button" className="link-btn">Olvidé mi contraseña</button>
            </div>

            {error ? <div className="login-error">{error}</div> : null}

            <button type="submit" className="login-submit" disabled={loading}>
              {loading ? 'Validando...' : 'Iniciar sesión'}
            </button>
          </form>
        </div>
      </div>
    </section>
  )
}