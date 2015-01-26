/* 
 * COS 561 Final Project: Equalized-latency routing
 * 1/11/2011
 * Gregory Finkelstein, Brandon Podmayersky, and Zhaoyang Xu 
 *
 * server.c
 * 
 * Sends a packet into the network to register a LEQ
 * service with the OpenFlow controller, and then receives
 * files from clients. 
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <ctype.h>
#include <unistd.h>
#include <strings.h>
#include <assert.h>
#include <sys/types.h>
#include <sys/socket.h>
#include <sys/ioctl.h>
#include <netinet/in.h>
#include <net/if.h>
#include <netdb.h>
#include <arpa/inet.h>

enum { FALSE = 0, TRUE = 1 };
enum { MAX_CLIENTS = 20 }; // We queue at most 20 clients.
enum { BUFFER_SIZE = 256 };

struct LEQrequest {
  uint32_t ipaddr;
  uint16_t protocol;
  uint16_t port;
  uint16_t alpha_percent; // To avoid dealing with float data, let's
  uint16_t x_percent;     // just have the client send a percentage
};                        // instead of a decimal.

static void register_LEQservice(uint16_t protocol, uint16_t port,
				uint16_t alpha_percent, uint16_t x_percent);
static int parseInt(const char* str);

int main(int argc, char* argv[]) {

  int port;              // The port number.
  struct sockaddr_in sa; // Socket address structure.
  int s;                 // The socket descriptor.
  char buf[BUFFER_SIZE]; // A buffer to receive messages.
  
  // Capture and validate the argument.
  if(argc != 2) {
    fprintf(stderr, "usage: %s <port>\n", argv[0]);
    exit(1);
  }
  port = parseInt(argv[1]);
  if(port < 0) {
    fprintf(stderr, "error: invalid port number: %s\n", argv[1]);
    exit(1);
  }

  printf("size of float is %d\n", sizeof(float));
  
  // Construct the address from the given port.
  bzero(&sa, sizeof(sa));
  sa.sin_family = AF_INET;
  sa.sin_port = htons(port);
  sa.sin_addr.s_addr = INADDR_ANY;
  
  // Create a socket.
  if((s = socket(PF_INET, SOCK_STREAM, 0)) < 0) {
    perror("socket error");
    exit(1);
  }
  
  // Bind the socket to our address.
  if(bind(s, (struct sockaddr*) &sa, sizeof(sa)) < 0) {
    perror("bind error");
    exit(1);
  }

  // Register the service as LEQ.
  register_LEQservice(IPPROTO_TCP, port, 10, 200);
  
  // We listen for MAX_CLIENTS connections.
  listen(s, MAX_CLIENTS);
  
  // The main loop: accept connections and then print any messages. */
  while(TRUE) {
    int cons; // The socket descriptor for one connection.
    socklen_t addrlen = sizeof(sa); // Address length.
    int msglen;  // Message length.
    
    // Accept a connection.
    if((cons = accept(s, (struct sockaddr*) &sa, &addrlen)) < 0) {
      perror("accept error");
      exit(1);
    }
    
    // Receive and print the message.
    while((msglen = recv(cons, buf, BUFFER_SIZE-1, 0))) {
      if(msglen < 0) {
	perror("recv error");
	exit(1);
      }
      // Print the string. It need not be null terminated, so
      // we add the terminator ourselves.
      buf[msglen] = '\0';
      printf("%s", buf);
      
      // The server does not exit cleanly, so flush output in case
      // it is being redirected to file.
      fflush(stdout);
    }
    
    // Close the connection.
    close(cons);
  }

  return 0;

}

/* Register the service on this machine with the given protocol and
 * port for LEQ. */
static void register_LEQservice(uint16_t protocol, uint16_t port,
				uint16_t alpha_percent, uint16_t x_percent) {

  int s; // The socket descriptor.
  struct hostent *hp;    // Structure for the host information.
  struct sockaddr_in sa; // Socket address structure.

  hp = gethostbyname("255.255.255.255");
  if(!hp) {
    fprintf(stderr, "host error");
    exit(1);
  }

  // Construct the address from the given host and port.
  bzero(&sa, sizeof(sa));
  sa.sin_family = AF_INET;
  sa.sin_port = htons(37823);
  bcopy(hp->h_addr, &sa.sin_addr, hp->h_length);

  // Create a socket that allows broadcast.
  if((s = socket(PF_INET, SOCK_DGRAM, 0)) < 0) {
    perror("socket error");
    exit(1);
  }
  int optval = 1;
  if(setsockopt(s, SOL_SOCKET, SO_BROADCAST, &optval, sizeof(optval)) < 0) {
    perror("setsockopt error");
    exit(1);
  }

  // Get our IP address.
  struct ifreq ifreqs[32];
  struct ifconf ifconf;
  memset(&ifconf, 0, sizeof(ifconf));
  ifconf.ifc_req = ifreqs;
  ifconf.ifc_len = sizeof(ifreqs);

  if(ioctl(s, SIOCGIFCONF, (char *) &ifconf) < 0) {
    perror("ioctl error");
    exit(1);
  }

  int i;
  for(i = 0; i < ifconf.ifc_len / sizeof(struct ifreq); i++) {
      printf("%s: %s\n", ifreqs[i].ifr_name, inet_ntoa(((struct sockaddr_in *)&ifreqs[i].ifr_addr)->sin_addr));
      printf("Integer is %d\n", ntohl(((struct sockaddr_in *)&ifreqs[i].ifr_addr)->sin_addr.s_addr));
      printf("Integer is %d\n", ((struct sockaddr_in *)&ifreqs[i].ifr_addr)->sin_addr.s_addr);
  }

  // Create the LEQ registration request and send it out.
  struct LEQrequest request;
  bzero(&request, sizeof(request));
  request.ipaddr = ((struct sockaddr_in *)&ifreqs[0].ifr_addr)->sin_addr.s_addr;
  request.protocol = htons(protocol);
  request.port = htons(port);
  request.alpha_percent = htons(alpha_percent);
  request.x_percent = htons(x_percent);

  printf("Sending data...\n", request.ipaddr, ntohl(request.ipaddr));

  int result = sendto(s,
		      (void*) &request,
		      sizeof(request),
		      0,
		      (struct sockaddr*) &sa,
		      sizeof(sa));

  printf("Sent %d bytes out of %d\n", result, sizeof(request));

  if(result < (int) sizeof(request)) {
    perror("sendto error");
    exit(1);
  }

  close(s);
  
}

static int parseInt(const char* str) {
  
  int value = 0; // The running total.
  int i = 0;
  
  if(str[0] == '\0') return -1;
  
  // Extract the number from left to right, multiplying by 10 to move the
  // digits into place.
  while(str[i] != '\0') {
    if(!isdigit(str[i])) return -1;
    value *= 10;
    value += str[i] - '0';
    i++;
  }
  
  return value;
}
