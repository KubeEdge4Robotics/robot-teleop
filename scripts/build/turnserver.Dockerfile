FROM alpine:3.9.2

LABEL mainterner="joeyhwong@gknow.cn"

ARG VERSION=4.5.0.8-r1
RUN apk update && \
    apk add --no-cache coturn=$VERSION

ENTRYPOINT ["/usr/bin/turnserver"]
CMD ["-v"]