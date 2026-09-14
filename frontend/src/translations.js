import React from 'react';

export const translations = {
  es: {
    // Navbar
    'navbar.toggleTheme': 'Alternar tema claro/oscuro',
    'navbar.toggleThemeDark': 'Cambiar a tema claro',
    'navbar.toggleThemeLight': 'Cambiar a tema oscuro',
    'navbar.home': 'Inicio',
    'navbar.logout': 'Cerrar sesión',
    'navbar.register': 'Registro',
    'navbar.portal': 'Portal Aspirantes',
    'navbar.panel': 'Mi Panel',
    'navbar.adminPanel': 'Panel de administración',
    'navbar.coordinacionPanel': 'Panel de Coordinación',
    'navbar.docentePanel': 'Panel del docente',
    'navbar.alumnoPanel': 'Panel del alumno',
    'navbar.contact': 'Contacto',
    'navbar.logoutMessage': 'Se cerró la sesión correctamente.',

    // Login
    'login.welcome': 'Bienvenido',
    'login.signIn': 'Iniciar sesión',
    'login.userOrEmail': 'Usuario o correo institucional',
    'login.userPlaceholder': 'admin / correo@institucion.edu.mx',
    'login.password': 'Contraseña',
    'login.passwordPlaceholder': 'Tu contraseña segura',
    'login.rememberMe': 'Recuérdame en este dispositivo',
    'login.forgotPassword': '¿Olvidaste tu contraseña?',
    'login.signInButton': 'Inicia sesión',
    'login.noAccount': '¿No tienes cuenta?',
    'login.registerHere': 'Regístrate aquí',
    'login.errorValidation': 'Captura usuario/correo y contraseña.',
    'login.errorCredentials': 'Usuario o contraseña incorrectos.',
    'login.errorConnection': 'No se pudo conectar con el servidor.',
    'login.institutionalAccess': 'Acceso institucional',
    'login.description': 'Un solo acceso para todas las personas del sistema. El perfil se identifica automáticamente según tus credenciales y te dirige al panel correcto.',
    'login.systemName': 'SINAC NEXT',
    'login.automaticProfile': 'Perfil automático',
    
    // Roles
    'role.aspirante': 'Aspirante',
    'role.alumno': 'Alumno',
    'role.coordinacion': 'Coordinación Académica',
    'role.docente': 'Docente',
    'role.director': 'Director de Tesis',
    'role.admin': 'Administrador',
    'role.servicios': 'Servicios Escolares',

    // Home
    'home.title': 'Bienvenido a SINAC NEXT',
    'home.subtitle': 'Sistema de Gestión Académica',
    'home.description': 'Accede con tus credenciales para continuar',
    'home.login': 'Iniciar sesión',
    'home.register': 'Registrarse como aspirante',

    // Messages
    'message.loggingOut': 'Cerrando sesión...',
    'message.loggedOut': 'Sesión cerrada correctamente',
  },
  en: {
    // Navbar
    'navbar.toggleTheme': 'Toggle light/dark theme',
    'navbar.toggleThemeDark': 'Switch to light theme',
    'navbar.toggleThemeLight': 'Switch to dark theme',
    'navbar.home': 'Home',
    'navbar.logout': 'Logout',
    'navbar.register': 'Register',
    'navbar.portal': 'Applicants Portal',
    'navbar.panel': 'My Panel',
    'navbar.adminPanel': 'Administration Panel',
    'navbar.coordinacionPanel': 'Coordination Panel',
    'navbar.docentePanel': 'Teacher Panel',
    'navbar.alumnoPanel': 'Student Panel',
    'navbar.contact': 'Contact',
    'navbar.logoutMessage': 'Session closed successfully.',

    // Login
    'login.welcome': 'Welcome',
    'login.signIn': 'Sign in',
    'login.userOrEmail': 'Username or institutional email',
    'login.userPlaceholder': 'admin / email@institution.edu.mx',
    'login.password': 'Password',
    'login.passwordPlaceholder': 'Your secure password',
    'login.rememberMe': 'Remember me on this device',
    'login.forgotPassword': 'Forgot your password?',
    'login.signInButton': 'Sign in',
    'login.noAccount': "Don't have an account?",
    'login.registerHere': 'Register here',
    'login.errorValidation': 'Please enter username/email and password.',
    'login.errorCredentials': 'Invalid username or password.',
    'login.errorConnection': 'Could not connect to the server.',
    'login.institutionalAccess': 'Institutional Access',
    'login.description': 'Single access for all system users. Your profile is identified automatically according to your credentials and directs you to the correct panel.',
    'login.systemName': 'SINAC NEXT',
    'login.automaticProfile': 'Automatic profile',

    // Roles
    'role.aspirante': 'Applicant',
    'role.alumno': 'Student',
    'role.coordinacion': 'Academic Coordination',
    'role.docente': 'Teacher',
    'role.director': 'Thesis Director',
    'role.admin': 'Administrator',
    'role.servicios': 'School Services',

    // Home
    'home.title': 'Welcome to SINAC NEXT',
    'home.subtitle': 'Academic Management System',
    'home.description': 'Access with your credentials to continue',
    'home.login': 'Sign in',
    'home.register': 'Register as an applicant',

    // Messages
    'message.loggingOut': 'Logging out...',
    'message.loggedOut': 'Session closed successfully',
  }
};

export function useLanguage() {
  const [language, setLanguage] = React.useState(() => {
    return typeof window !== 'undefined' ? localStorage.getItem('sinac_language') || 'es' : 'es';
  });

  React.useEffect(() => {
    const handleLanguageChange = () => {
      const lang = localStorage.getItem('sinac_language') || 'es';
      setLanguage(lang);
    };

    window.addEventListener('sinac:language-changed', handleLanguageChange);
    return () => window.removeEventListener('sinac:language-changed', handleLanguageChange);
  }, []);
  
  return {
    language,
    t: (key) => translations[language]?.[key] || translations.es[key] || key,
    setLanguage: (lang) => {
      localStorage.setItem('sinac_language', lang);
      window.dispatchEvent(new Event('sinac:language-changed'));
    }
  };
}
