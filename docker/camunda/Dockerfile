# Camunda 7 Community ya no se publica en Docker Hub: la imagen base debe existir localmente
# (docker tag camunda/camunda-bpm-platform:latest camunda/camunda-bpm-platform:7.24.0).
FROM camunda/camunda-bpm-platform:7.24.0

RUN rm -rf webapps/camunda-invoice webapps/examples webapps/docs webapps/manager webapps/host-manager

COPY engine-rest-web.xml webapps/engine-rest/WEB-INF/web.xml
