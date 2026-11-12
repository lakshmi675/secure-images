# syntax=docker/dockerfile:1.7
ARG JDK_IMAGE
ARG BASE_IMAGE

############################################################
# 1. Build Tomcat from PGP+SHA512-verified upstream source
#    (bytecode is arch-independent -> run on build host)
############################################################
FROM --platform=$BUILDPLATFORM ${JDK_IMAGE} AS tomcat-build
ARG TOMCAT_VERSION
ARG TOMCAT_MAJOR
RUN apt-get update \
 && apt-get install -y --no-install-recommends ant gnupg curl ca-certificates \
 && rm -rf /var/lib/apt/lists/*
WORKDIR /src
COPY keys/KEYS-tomcat-${TOMCAT_MAJOR} /keys/KEYS
RUN set -eux; \
    base="https://archive.apache.org/dist/tomcat/tomcat-${TOMCAT_MAJOR}/v${TOMCAT_VERSION}/src"; \
    f="apache-tomcat-${TOMCAT_VERSION}-src.tar.gz"; \
    curl -fsSLO "$base/$f"; curl -fsSLO "$base/$f.asc"; curl -fsSLO "$base/$f.sha512"; \
    sha512sum -c "$f.sha512"; \
    export GNUPGHOME="$(mktemp -d)"; \
    gpg --batch --import /keys/KEYS; \
    gpg --batch --verify "$f.asc" "$f"; \
    tar xzf "$f" --strip-components=1; \
    rm -f "$f" "$f.asc" "$f.sha512"
RUN ant -Dbase.path=/deps deploy

############################################################
# 2. Harden the distribution
############################################################
FROM tomcat-build AS tomcat-dist
COPY rootfs/conf/ /tmp/conf/
RUN set -eux; \
    mkdir -p /dist && cp -a output/build/. /dist/ && cd /dist; \
    rm -rf webapps/* logs/* temp/* work/*; \
    find bin -type f ! -name bootstrap.jar ! -name tomcat-juli.jar -delete; \
    cp /tmp/conf/server.xml /tmp/conf/logging.properties conf/; \
    mkdir -p webapps logs temp work conf/Catalina/localhost; \
    chmod -R go-w,a+rX /dist; \
    mkdir -p /writable && mv logs temp work /writable/

############################################################
# 3. Minimal JRE via jlink (per target platform)
############################################################
FROM ${JDK_IMAGE} AS jre
ARG JRE_MODULES
RUN jlink --strip-debug --no-man-pages --no-header-files --compress=2 \
          --add-modules "${JRE_MODULES}" --output /opt/jre

############################################################
# 4. Final image - no shell, no package manager, non-root
############################################################
FROM ${BASE_IMAGE}
COPY --from=jre /opt/jre /opt/java
COPY --from=tomcat-dist /dist/ /opt/tomcat/
COPY --from=tomcat-dist --chown=65532:65532 /writable/ /opt/tomcat/
ENV JAVA_HOME=/opt/java CATALINA_HOME=/opt/tomcat CATALINA_BASE=/opt/tomcat \
    JAVA_TOOL_OPTIONS="-XX:MaxRAMPercentage=75.0 -XX:+ExitOnOutOfMemoryError"
USER 65532:65532
WORKDIR /opt/tomcat
EXPOSE 8080
ENTRYPOINT ["/opt/java/bin/java", \
  "--add-opens=java.base/java.lang=ALL-UNNAMED", \
  "--add-opens=java.base/java.io=ALL-UNNAMED", \
  "--add-opens=java.base/java.util=ALL-UNNAMED", \
  "--add-opens=java.base/java.util.concurrent=ALL-UNNAMED", \
  "--add-opens=java.rmi/sun.rmi.transport=ALL-UNNAMED", \
  "-Djava.util.logging.manager=org.apache.juli.ClassLoaderLogManager", \
  "-Djava.util.logging.config.file=/opt/tomcat/conf/logging.properties", \
  "-Dcatalina.home=/opt/tomcat", "-Dcatalina.base=/opt/tomcat", \
  "-Djava.io.tmpdir=/opt/tomcat/temp", \
  "-cp", "/opt/tomcat/bin/bootstrap.jar:/opt/tomcat/bin/tomcat-juli.jar", \
  "org.apache.catalina.startup.Bootstrap", "start"]
