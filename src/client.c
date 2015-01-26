/*
 * COS 561 Final Project: Equalized-latency routing
 * 1/11/2011
 * Gregory Finkelstein, Brandon Podmayersky, and Zhaoyang Xu
 *
 * client.c
 * 
 * Send the input from stdin to the specified server:
 * client <server IP or hostname> <port>
 *
 */

#include <stdio.h>
#include <stdlib.h>
#include <ctype.h>
#include <unistd.h>
#include <strings.h>
#include <string.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <netdb.h>

enum { FALSE = 0, TRUE = 1 };
enum { BUFFER_SIZE = 256 };

static int parseInt(const char* str);

/*-------------------------------------------------------------------------*/

/* Send a text message from stdin to the server. */
int main(int argc, char * argv[]) {

	int port;              // The port number.
	struct hostent *hp;    // Structure for the host information.
	struct sockaddr_in sa; // Socket address structure.
	int s;                 // The socket descriptor.
	int readNewline;	   // Should the next newline cause the program to exit?
	char buf[BUFFER_SIZE]; // A buffer to receive messages.

	// Validate and capture the arguments.
	if(argc != 3) {
		fprintf(stderr, "usage: %s <hostname> <port>\n", argv[0]);
		exit(1);
	}
	// Get the port number.
	port = parseInt(argv[2]);
	if(port < 0) {
		fprintf(stderr, "error: invalid port number: %s\n", argv[1]);
		exit(1);
	}
	
	// Get the host IP address.
	hp = gethostbyname(argv[1]);
	if(!hp) {
		fprintf(stderr, "host error: could not locate %s\n", argv[1]);
		exit(1);
	}

	// Construct the address from the given host and port.
	bzero(&sa, sizeof(sa));
	sa.sin_family = AF_INET;
	sa.sin_port = htons(port);
	bcopy(hp->h_addr, &sa.sin_addr, hp->h_length);

	// Create a socket.
	if((s = socket(PF_INET, SOCK_STREAM, 0)) < 0) {
		perror("socket error");
		exit(1);
	}

	// Connect to the server.
	if(connect(s, (struct sockaddr*) &sa, sizeof(sa)) < 0) {
		perror("connect error");
		close(s);
		exit(1);
	}

	readNewline = FALSE;

	// Get the input from stdin and send the message to the server.
	while(fgets(buf, BUFFER_SIZE, stdin)) {
		int len = strlen(buf);
		int sentTot = 0;
		int sent;

		// If we just read a newline, exit if we read another.
		if(readNewline && buf[0] == '\n')
			exit(0);

		// Otherwise update whether the last character read is newline.
		// Sufficient since fgets() stops after reading \n.
		if(buf[len - 1] == '\n') readNewline = TRUE;
		else readNewline = FALSE;

		// Finally, send the message.
		while(sentTot < len) {
			if((sent = send(s, buf + sentTot, len - sentTot, 0)) < 0) {
				perror("send error");
				exit(1);
			}
			sentTot += sent;
		}

	}

	return 0;
}

/*-------------------------------------------------------------------------*/

/* Parse a nonnegative integer from the given string or return
 * -1 if the given string does not represent a nonnegative integer. */
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


