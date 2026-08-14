from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from .views import PreregistroCreateView, MiPerfilView, PanelAdministradorView, PanelCoordinacionView, EstadoAspiranteCoordinacionView, AspiranteCoordinacionDetailView, SolicitarApoyoView, InicioSesionView, DocumentoAspiranteView, DocumentoDescargaView, SeguimientoAspiranteView, MarcarNotificacionesLeidasView, MisMateriasDisponiblesView, MisInscripcionesView, SolicitudAcademicaView, HorarioDescargaView, ReinscripcionDescargaView, MateriasListView, CursosUploadView, GenerarCargaView, CalificacionesDownloadView, AdscripcionDownloadView, DarBajaView, ConvertirAlumnoView, ConvertirMismaCuentaView

urlpatterns = [
    path('preregistro/',    PreregistroCreateView.as_view(), name='preregistro-create'),
    path('preregistro/me/', MiPerfilView.as_view(),          name='preregistro-me'),
    path('preregistro/seguimiento/', SeguimientoAspiranteView.as_view(), name='seguimiento-aspirante'),
    path('preregistro/documentos/', DocumentoAspiranteView.as_view(), name='documentos-aspirante'),
    path('preregistro/documentos/<int:pk>/', DocumentoAspiranteView.as_view(), name='documento-aspirante'),
    path('preregistro/documentos/<int:pk>/descarga/', DocumentoDescargaView.as_view(), name='documento-descarga'),
    path('administracion/panel/', PanelAdministradorView.as_view(), name='admin-panel'),
    path('administracion/aspirantes/<int:pk>/', PanelAdministradorView.as_view(), name='admin-aspirante-detail'),
    path('coordinacion/panel/', PanelCoordinacionView.as_view(), name='coordinacion-panel'),
    path('coordinacion/aspirantes/<int:pk>/estado/', EstadoAspiranteCoordinacionView.as_view(), name='coordinacion-estado-aspirante'),
    path('coordinacion/aspirantes/<int:pk>/', AspiranteCoordinacionDetailView.as_view(), name='coordinacion-aspirante-detail'),
    path('coordinacion/materias/',                MateriasListView.as_view(), name='coordinacion-materias'),
    path('coordinacion/cursos/upload/',           CursosUploadView.as_view(), name='coordinacion-cursos-upload'),
    path('coordinacion/cargas/generar/',          GenerarCargaView.as_view(), name='coordinacion-cargas-generar'),
    path('coordinacion/aspirantes/<int:pk>/calificaciones/', CalificacionesDownloadView.as_view(), name='coordinacion-calificaciones'),
    path('coordinacion/aspirantes/<int:pk>/adscripcion/download/', AdscripcionDownloadView.as_view(), name='coordinacion-adscripcion-download'),
    path('coordinacion/aspirantes/<int:pk>/dar_baja/', DarBajaView.as_view(), name='coordinacion-dar-baja'),
    path('coordinacion/aspirantes/<int:pk>/convertir/',           ConvertirAlumnoView.as_view(), name='coordinacion-convertir-alumno'),
    path('preregistro/apoyo/solicitar/', SolicitarApoyoView.as_view(), name='solicitar-apoyo'),
    path('preregistro/notificaciones/marcar-leidas/', MarcarNotificacionesLeidasView.as_view(), name='marcar-notificaciones-leidas'),
    path('preregistro/convertir-misma-cuenta/', ConvertirMismaCuentaView.as_view(), name='convertir-misma-cuenta'),
    path('preregistro/materias/', MisMateriasDisponiblesView.as_view(), name='materias-disponibles'),
    path('preregistro/inscripciones/', MisInscripcionesView.as_view(), name='mis-inscripciones'),
    path('preregistro/solicitudes-academicas/', SolicitudAcademicaView.as_view(), name='solicitudes-academicas'),
    path('preregistro/horario/download/', HorarioDescargaView.as_view(), name='horario-descarga'),
    path('preregistro/reinscripcion/download/', ReinscripcionDescargaView.as_view(), name='reinscripcion-descarga'),
    path('auth/login/',     InicioSesionView.as_view(),       name='token-obtain'),
    path('auth/refresh/',   TokenRefreshView.as_view(),      name='token-refresh'),
]
