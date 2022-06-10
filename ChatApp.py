import sys
from client import Client
from server import Server

# class ChatApp:
#     '''ChatApp object that defines modes and check the input args'''
#     def __init__(self, mode, args):
#         if mode == '-c':
#             print(">>> Welcome, You are registered.")
#             self.name, self.server_IP, self.server_port, self.client_port = args
#         if mode == '-s':
#             self.port = args
        

def checkIP(s):
    try: return str(int(s)) == s and 0 <= int(s) <= 255
    except: return False

def checkPort(n): # also need to verify it's not decimal
    try: return str(int(n)) == n and 1024 <= int(n) <= 65535
    except: return False

def main():
    if len(sys.argv) < 3:
        sys.exit("Not enough input args for either server or client.")

    if sys.argv[1] == '-s': # -s mode
        if len(sys.argv) != 3: 
            sys.exit("Input not valid. Require 1 arg for server mode, but received " + str(len(sys.argv)-1))
        if not checkPort(sys.argv[2]):
            sys.exit("Invalid port number. Should be in the range 1024-65535.")

        # Error checks clear. Make server instance.
        Server(int(sys.argv[2]))
    
    elif sys.argv[1] == '-c': # -c mode
        if len(sys.argv) != 6: # check if the input is valid 
            sys.exit("Input not valid. Require 4 args for client mode, but received " + str(len(sys.argv)-1))
        
        if ',' in sys.argv[2]:
            sys.exit("Invalid user nickname! Please avoid white space, commma ',' and angle brackets '<''>'")

        # check if IP address is valid (4 blocks separated by periods and each block lies in 0-255)
        IP = sys.argv[3]
        if IP.count(".") != 3 or not all(checkIP(i) for i in IP.split(".")):
            sys.exit("Invlid IPv4 Address.")

        # check if port numbers are valid and in the range 1024-65535.
        if not checkPort(sys.argv[4]) or not checkPort(sys.argv[5]):
            sys.exit("Invalid port number. Should be in the range 1024-65535.")
        
        # Error checks clear, Make client instance.
        Client(sys.argv[2], sys.argv[3], int(sys.argv[4]), int(sys.argv[5]))

    else:
        sys.exit("Input not valid. Use -s for server mode and -c for client mode.")


if __name__ == '__main__':
	main()