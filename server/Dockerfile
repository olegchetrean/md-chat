# SPDX-License-Identifier: AGPL-3.0-only
# SPDX-FileCopyrightText: 2026 Mega Promoting SRL
#
# MD-Chat Server — multi-stage Docker build.
#
# Stage 1 (overlay-builder): clone upstream Synapse at a pinned tag, copy our
# overlays into place, run apply-overlays.sh + verify-overlays.sh.
# Stage 2 (runtime): start from python:3.12-slim, pip-install the patched
# Synapse source tree, set up the runtime user.
#
# Build:
#   docker build -t mdchat-synapse:dev .
# Override Synapse version:
#   docker build --build-arg SYNAPSE_VERSION=v1.122.0 -t mdchat-synapse:dev .

ARG SYNAPSE_VERSION=v1.121.0
ARG SYNAPSE_REPO=https://github.com/element-hq/synapse.git
ARG SOURCE_DISCLOSURE_URL=https://github.com/megapromoting/md-chat-server

# -----------------------------------------------------------------------------
# Stage 1 — overlay builder
# -----------------------------------------------------------------------------
FROM python:3.12-slim AS overlay-builder

ARG SYNAPSE_VERSION
ARG SYNAPSE_REPO

RUN apt-get update \
    && apt-get install --no-install-recommends -y \
         git ca-certificates patch yq \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build

# Shallow-clone upstream Synapse at the pinned tag. Shallow because we never
# rebase inside the container — the rebase happens in our git repo, the
# container just consumes the result.
RUN git clone --depth 1 --branch "${SYNAPSE_VERSION}" "${SYNAPSE_REPO}" synapse-src \
    && cd synapse-src \
    && echo "Upstream Synapse ${SYNAPSE_VERSION} at $(git rev-parse HEAD)" \
       > /build/UPSTREAM_REVISION

# Copy our overlay tree and scripts.
COPY overlays/ /build/overlays/
COPY scripts/  /build/scripts/
RUN chmod +x /build/scripts/*.sh

# Apply overlays deterministically. If anything fails (patch reject, missing
# string match), the build aborts here.
RUN /build/scripts/apply-overlays.sh /build/synapse-src /build/overlays \
    && /build/scripts/verify-overlays.sh /build/synapse-src /build/overlays

# -----------------------------------------------------------------------------
# Stage 2 — runtime
# -----------------------------------------------------------------------------
FROM python:3.12-slim AS runtime

ARG SYNAPSE_VERSION
ARG SOURCE_DISCLOSURE_URL

LABEL org.opencontainers.image.title="MD-Chat Server"
LABEL org.opencontainers.image.description="Matrix homeserver — MD-Chat fork of Element Synapse (AGPLv3)"
LABEL org.opencontainers.image.vendor="Mega Promoting SRL"
LABEL org.opencontainers.image.licenses="AGPL-3.0-only"
LABEL org.opencontainers.image.source="${SOURCE_DISCLOSURE_URL}"
LABEL org.opencontainers.image.documentation="https://md-chat.eu/help"
LABEL eu.md-chat.synapse-version="${SYNAPSE_VERSION}"

RUN apt-get update \
    && apt-get install --no-install-recommends -y \
         build-essential libpq-dev libffi-dev libjpeg-dev libssl-dev libxslt1-dev \
         curl ca-certificates gosu \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --system --gid 991 mdchat \
    && useradd  --system --uid 991 --gid 991 --home /data --shell /bin/false mdchat

WORKDIR /opt/mdchat-synapse

# Copy the patched Synapse source from stage 1 and install it as a package.
COPY --from=overlay-builder /build/synapse-src/   /opt/mdchat-synapse/synapse-src/
COPY --from=overlay-builder /build/UPSTREAM_REVISION /opt/mdchat-synapse/UPSTREAM_REVISION

RUN cd /opt/mdchat-synapse/synapse-src \
    && pip install --no-cache-dir --upgrade pip poetry \
    && pip install --no-cache-dir ".[postgres,redis,saml2,oidc,systemd,url-preview]"

# Mount the templates overlay where homeserver.yaml expects it
# (templates.custom_template_directory: /data/templates/mdchat/).
RUN mkdir -p /data/templates/mdchat
COPY --from=overlay-builder /build/overlays/templates/  /opt/mdchat-synapse/templates-default/
# A startup hook (entrypoint) copies templates-default → /data/templates/mdchat
# on first run if the volume is empty.

COPY --from=overlay-builder /build/scripts/  /opt/mdchat-synapse/scripts/

VOLUME ["/data"]
EXPOSE 8008 8448

USER mdchat

ENV SYNAPSE_CONFIG_DIR=/data
ENV SYNAPSE_CONFIG_PATH=/data/homeserver.yaml
ENV SYNAPSE_DATA_DIR=/data
ENV MD_CHAT_SOURCE_URL="${SOURCE_DISCLOSURE_URL}"

ENTRYPOINT ["python", "-m", "synapse.app.homeserver"]
CMD ["--config-path=/data/homeserver.yaml"]
