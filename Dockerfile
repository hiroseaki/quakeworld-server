# syntax=docker/dockerfile:1.7
FROM debian:bookworm-slim AS builder

ARG MVDSV_COMMIT=b4fdca1808ab5ec89669d284f3d3f8d244b7c5b7
ARG KTX_COMMIT=ce329889f97cc5bacf85b6388d3c5d8f242769fd
ARG QWFWD_COMMIT=519b6734d50b42f32857eed3cad9fbd3bb7029de

RUN apt-get update \
 && apt-get install -y --no-install-recommends \
      build-essential ca-certificates cmake git libcurl4-openssl-dev \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /src
RUN git clone --filter=blob:none https://github.com/QW-Group/mvdsv.git \
 && cd mvdsv \
 && git checkout --detach "${MVDSV_COMMIT}" \
 && test "$(git rev-parse HEAD)" = "${MVDSV_COMMIT}" \
 && git submodule update --init --recursive \
 && cmake -S . -B build -DCMAKE_BUILD_TYPE=Release -DGIT_SUBMODULE=OFF \
      -DPCRE_INCLUDE_DIR=/src/mvdsv/src/pcre \
 && cmake --build build --parallel

RUN git clone --filter=blob:none https://github.com/QW-Group/ktx.git \
 && cd ktx \
 && git checkout --detach "${KTX_COMMIT}" \
 && test "$(git rev-parse HEAD)" = "${KTX_COMMIT}" \
 && cmake -S . -B build -DCMAKE_BUILD_TYPE=Release \
 && cmake --build build --parallel

RUN git clone --filter=blob:none https://github.com/QW-Group/qwfwd.git \
 && cd qwfwd \
 && git checkout --detach "${QWFWD_COMMIT}" \
 && test "$(git rev-parse HEAD)" = "${QWFWD_COMMIT}" \
 && cmake -S . -B build -DCMAKE_BUILD_TYPE=Release \
 && cmake --build build --parallel

# The final image accompanies the GPL binaries with their corresponding source.
RUN mkdir -p /out/source \
 && cp -a /src/mvdsv /out/source/mvdsv \
 && cp -a /src/ktx /out/source/ktx \
 && cp -a /src/qwfwd /out/source/qwfwd \
 && rm -rf /out/source/qwfwd/.git /out/source/qwfwd/build \
 && rm -rf /out/source/mvdsv/.git /out/source/mvdsv/build \
      /out/source/ktx/.git /out/source/ktx/build \
 && rm -f /out/source/mvdsv/src/qwprot/.git \
 && printf 'MVDSV %s\nKTX %s\nQWFWD %s\n' "${MVDSV_COMMIT}" "${KTX_COMMIT}" "${QWFWD_COMMIT}" > /out/source/SOURCE-COMMITS

FROM golang:1.25-bookworm AS qtv-builder
ARG QTV_COMMIT=025ca949aca06cad6777de0075148ac06a15f4f0
RUN git clone https://github.com/QW-Group/qtv.git /src/qtv
WORKDIR /src/qtv
RUN git checkout --detach "${QTV_COMMIT}" \
 && test "$(git rev-parse HEAD)" = "${QTV_COMMIT}" \
 && go mod download \
 && CGO_ENABLED=0 go build -mod=readonly -trimpath -o /out/qtv ./cmd/qtv \
 && go mod vendor \
 && printf 'QTV %s\n' "${QTV_COMMIT}" > SOURCE-COMMITS \
 && rm -rf .git

# BSPs are architecture-independent; download and verify once at build time.
FROM --platform=$BUILDPLATFORM debian:bookworm-slim AS map-builder
RUN apt-get update \
 && apt-get install -y --no-install-recommends python3 curl ca-certificates \
 && rm -rf /var/lib/apt/lists/*
COPY scripts/fetch-ra-maps.py /fetch-ra-maps.py
RUN python3 /fetch-ra-maps.py /maps

FROM debian:bookworm-slim

ARG MVDSV_VERSION=1.20-dev
ARG KTX_VERSION=1.47
ARG QWFWD_VERSION=1.30
ARG VCS_REF=unknown
ARG BUILD_DATE=unknown
ARG SOURCE_URL=https://github.com/hiroseaki/quakeworld-server
LABEL org.opencontainers.image.title="QuakeWorld Server" \
      org.opencontainers.image.description="MVDSV/KTX servers, QTV and QWFWD" \
      org.opencontainers.image.version="MVDSV ${MVDSV_VERSION} / KTX ${KTX_VERSION} / QWFWD ${QWFWD_VERSION}" \
      org.opencontainers.image.source="${SOURCE_URL}" \
      org.opencontainers.image.revision="${VCS_REF}" \
      org.opencontainers.image.created="${BUILD_DATE}" \
      org.opencontainers.image.licenses="GPL-2.0-only AND MIT AND BSD-2-Clause"

RUN apt-get update \
 && apt-get install -y --no-install-recommends libcurl4 python3 ca-certificates \
 && rm -rf /var/lib/apt/lists/* \
 && groupadd --gid 10001 quake \
 && useradd --uid 10001 --gid quake --home-dir /nquake --no-create-home quake \
 && mkdir -p /nquake/id1 /nquake/qw/maps /nquake/qw/locs \
      /nquake/ktx/runtime /nquake/ktx/demos /nquake/logs \
 && chown -R 10001:10001 /nquake

COPY --from=builder --chown=10001:10001 /src/mvdsv/build/mvdsv /nquake/mvdsv
COPY --from=builder --chown=10001:10001 /src/ktx/build/qwprogs.so /nquake/ktx/qwprogs.so
COPY --from=builder --chown=10001:10001 /src/ktx/resources/example-configs/ktx/ /nquake/ktx/
COPY --from=builder /out/source/ /usr/src/quakeworld/
COPY --from=builder /src/qwfwd/build/qwfwd /usr/local/bin/qwfwd
COPY --from=qtv-builder /out/qtv /usr/local/bin/qtv
COPY --from=qtv-builder /src/qtv /usr/src/quakeworld/qtv
COPY --from=map-builder --chown=10001:10001 /maps/ /nquake/ktx/maps/
COPY scripts/fetch-ra-maps.py /usr/src/quakeworld/container/fetch-ra-maps.py
COPY runtime/ /usr/local/lib/quakeworld/
COPY LICENSE THIRD_PARTY_NOTICES.md /usr/share/doc/quakeworld/
COPY Dockerfile entrypoint.sh /usr/src/quakeworld/container/
COPY --chown=10001:10001 config/container-base.cfg /nquake/ktx/container-base.cfg
COPY --chown=10001:10001 config/ffa-default.cfg /nquake/ktx/configs/usermodes/ffa/default.cfg
COPY config/server.cfg /nquake/ktx/server.cfg
COPY config/reset.cfg /nquake/ktx/configs/reset.cfg
COPY config/mapcycle.txt /etc/quakeworld/ffa-mapcycle.txt
COPY config/ctf-mapcycle.txt config/ra-mapcycle.txt /etc/quakeworld/
COPY --from=builder --chown=10001:10001 /src/ktx/resources/example-configs/id1/maps/ctf/ /nquake/ktx/maps/ctf/
COPY --from=builder --chown=10001:10001 /src/ktx/resources/example-configs/id1/maps/arena3.ent /src/ktx/resources/example-configs/id1/maps/arena5.ent /nquake/ktx/maps/ra/
COPY entrypoint.sh /usr/local/bin/quakeworld-entrypoint

RUN printf '\nexec runtime/arena.cfg\n' >> /nquake/ktx/configs/usermodes/1on1/default.cfg

RUN chmod 0755 /nquake/mvdsv /usr/local/bin/quakeworld-entrypoint

USER 10001:10001
WORKDIR /nquake
EXPOSE 27500/udp 27500/tcp 28000/tcp 30000/udp
STOPSIGNAL SIGINT
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 CMD ["python3", "/usr/local/lib/quakeworld/healthcheck.py"]
ENTRYPOINT ["/usr/local/bin/quakeworld-entrypoint"]
