# syntax=docker/dockerfile:1.7
FROM debian:bookworm-slim AS builder

ARG MVDSV_COMMIT=11166a7f2a12838198ba253baa316c215271e357
ARG KTX_COMMIT=ce329889f97cc5bacf85b6388d3c5d8f242769fd

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

# The final image accompanies the GPL binaries with their corresponding source.
RUN mkdir -p /out/source \
 && cp -a /src/mvdsv /out/source/mvdsv \
 && cp -a /src/ktx /out/source/ktx \
 && rm -rf /out/source/mvdsv/.git /out/source/mvdsv/build \
      /out/source/ktx/.git /out/source/ktx/build \
 && rm -f /out/source/mvdsv/src/qwprot/.git \
 && printf 'MVDSV %s\nKTX %s\n' "${MVDSV_COMMIT}" "${KTX_COMMIT}" > /out/source/SOURCE-COMMITS

COPY src/qw-healthcheck.c /src/qw-healthcheck.c
RUN cc -O2 -Wall -Wextra -Werror -o /src/qw-healthcheck /src/qw-healthcheck.c

FROM debian:bookworm-slim

ARG MVDSV_VERSION=1.11
ARG KTX_VERSION=1.47
ARG VCS_REF=unknown
ARG BUILD_DATE=unknown
ARG SOURCE_URL=https://github.com/OWNER/quakeworld-server-docker
LABEL org.opencontainers.image.title="QuakeWorld Server" \
      org.opencontainers.image.description="Hardened MVDSV/KTX FFA server image" \
      org.opencontainers.image.version="MVDSV ${MVDSV_VERSION} / KTX ${KTX_VERSION}" \
      org.opencontainers.image.source="${SOURCE_URL}" \
      org.opencontainers.image.revision="${VCS_REF}" \
      org.opencontainers.image.created="${BUILD_DATE}" \
      org.opencontainers.image.licenses="GPL-2.0-only AND MIT"

RUN apt-get update \
 && apt-get install -y --no-install-recommends libcurl4 \
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
COPY --from=builder /src/qw-healthcheck /usr/local/bin/qw-healthcheck
COPY --chown=10001:10001 config/container-base.cfg /nquake/ktx/container-base.cfg
COPY --chown=10001:10001 config/ffa-default.cfg /nquake/ktx/configs/usermodes/ffa/default.cfg
COPY --chown=10001:10001 entrypoint.sh /usr/local/bin/quakeworld-entrypoint

RUN chmod 0755 /nquake/mvdsv /usr/local/bin/qw-healthcheck /usr/local/bin/quakeworld-entrypoint

USER 10001:10001
WORKDIR /nquake
EXPOSE 27500/udp
STOPSIGNAL SIGINT
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 CMD ["/usr/local/bin/qw-healthcheck"]
ENTRYPOINT ["/usr/local/bin/quakeworld-entrypoint"]
