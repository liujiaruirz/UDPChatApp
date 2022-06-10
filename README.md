## Project Description

A Python Chat application that uses UDP socket to transport messages. The application serves the functions of (de-)registration, direct message, group message, and offline chat. For direct message, the client directly sends messages to the recipient without transporting through the server. The server saves chats (direct and group) for the offline clients and sends them to the client once it is registered again.

## Command-line Instructions

The program adheres the command operations mentioned in the assignment spec (except for send_all): 

### Start Server: python3 ChatApp.py -s <serverPort>

### Registration: python3 ChatApp.py -c <nickname> <serverIP> <serverPort> <clientPort>

For local machine use, use 127.0.0.1 for localhost.

Once initiated server and clients, the commands for clients are as follows:

#### Direct Chat: send <name> <message>
#### De-registration: dereg <nick-name>
#### Log Back: reg <nick-name>
#### Group Chat: send_all <message> --------- note that no global brackets here, which is shown in assignment spec.


## Implementation Details

### Overall construction
The file ChatApp.py is used to create server/client instances.
The server instance contains one main thread that listens the messages/operations from clients.
The client instance contains two threads: input and listen.
	-- The input thread is used to ask for user's input and direct actions to specific functions.
	-- The listen thread is used to receive messages from other clients/server. 

### Timeout Implementation
The client instance contains several self variables to detect if ACK received during a period.
When the client needs to get an ACK, set the current thread (usually input thread) sleep (for 5 msecs) and change the specific self variable to True.
Once the required ACK received in listen thread, change the self variable to False.
When the input thread wakes up, if the variable is False, it means ACK received. Otherwise, timeout.

The server instance contains two self variables to detect if ACK received or timeout. 
When the server needs to get an ACK, create a new thread that listens ACK. The new thread performs similar to the client.

### Data Structures
For client to client, client to server, and server to client transportations, since socket requires bytes type, I concatenate and convert every message and informations(e.g., timestamp, senderPort, IP, etc) to string before transporting.

Save Chats are stored as dict of list of vectors as below:
{name of recipient clients: [(Sender1, timestamp, message), (Sender2, timestamp, message), ...]}

### Known Bugs & Assumptions:
ASSUMPTION: No two users use the same Port of the same Address.
1. Please avoid comma ',', whitespace ' ', and brackets '<' '>' in the name.
2. Please avoid symbols '&' and '|' in the message. (Because the program used the two symbols to separate the saved chats when converting to string). But can use whitespace :)
3. Sometimes the prompt '>>>' could be misplaced or missing. This is because a new prompt only shows when one command is taken. If a message or system information (from server) is received, there wouldn't be a prompt at the new line. Although I tried to hard code to avoid problem, it still happens rarely.
