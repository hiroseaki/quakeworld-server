#include <arpa/inet.h>
#include <errno.h>
#include <netinet/in.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <sys/time.h>
#include <unistd.h>

int main(void) {
    const char *port_env = getenv("QW_PORT");
    long port = port_env ? strtol(port_env, NULL, 10) : 27500;
    if (port < 1 || port > 65535) return 2;

    int fd = socket(AF_INET, SOCK_DGRAM, 0);
    if (fd < 0) return 2;

    struct timeval timeout = {.tv_sec = 2, .tv_usec = 0};
    if (setsockopt(fd, SOL_SOCKET, SO_RCVTIMEO, &timeout, sizeof(timeout)) != 0) {
        close(fd);
        return 2;
    }

    struct sockaddr_in server = {0};
    server.sin_family = AF_INET;
    server.sin_port = htons((unsigned short)port);
    server.sin_addr.s_addr = htonl(INADDR_LOOPBACK);

    const unsigned char request[] = {0xff, 0xff, 0xff, 0xff, 's', 't', 'a', 't', 'u', 's', '\n'};
    if (sendto(fd, request, sizeof(request), 0, (struct sockaddr *)&server, sizeof(server)) < 0) {
        close(fd);
        return 1;
    }

    unsigned char response[4096];
    ssize_t n = recvfrom(fd, response, sizeof(response), 0, NULL, NULL);
    close(fd);
    if (n < 5) return 1;
    return response[0] == 0xff && response[1] == 0xff && response[2] == 0xff && response[3] == 0xff ? 0 : 1;
}
