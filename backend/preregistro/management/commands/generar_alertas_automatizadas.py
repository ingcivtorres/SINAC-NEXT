from django.core.management.base import BaseCommand

from preregistro.alertas import generar_alertas_automatizadas


class Command(BaseCommand):
    help = 'Genera alertas automáticas de bajas, vencimientos de inscripción y apoyos académicos.'

    def handle(self, *args, **options):
        resultado = generar_alertas_automatizadas()
        self.stdout.write(self.style.SUCCESS(
            f"Alertas generadas: {resultado['total']} "
            f"(bajas={resultado['bajas']}, vencimientos={resultado['vencimientos']}, becas={resultado['becas']})."
        ))
