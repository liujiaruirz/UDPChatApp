from socket import *
from threading import Thread
import time
import sys, os

class Client:
    def __init__(self, name, serverIP, serverPort, clientPort):
        '''
        Client Object. Contains two threads - user input and listen from other client or from the server
        '''
        self.regTable = {}
        self.serverIP = serverIP
        self.serverPort = serverPort
        self.name = name
        self.status = True # client offline or online
        self.msgIsWaiting = False # object variable for direct msg to determine if target client timeout
        self.derIsWaiting = False # for dereg ack to determine if timeout
        self.gcIsWaiting = False # for group chat ack to determine if timeout
        self.serIsWaiting = False # for direct msg to determine if server timeout
        
        # register client on server
        self.clientSocket = socket(AF_INET, SOCK_DGRAM)
        self.clientSocket.bind(('', clientPort))
        clientInfo = '<r>' + name
        self.clientSocket.sendto(clientInfo.encode(), (serverIP, serverPort))
        
        t_listen = Thread(target=self.listen)
        t_input = Thread(target=self.userInput)
        t_input.daemon = True # make t_input auxiliary thread
        t_input.start()
        t_listen.start()

    def listen(self):
        '''
        Listen from other clients or from the server. Differentiate actions and direct them to specific functions.
        '''
        while True:
            # read from UDP socket into message
            message, senderAddress = self.clientSocket.recvfrom(2048)
            modifiedMessage = message.decode()
            # the first four characters <xx> contain the operation given by the server
            action = modifiedMessage[:4]
            # while online
            if self.status:
                if action == '<bc>':
                    # received broadcast
                    self.updateTable(modifiedMessage[4:])
                    # print(self.regTable)
                    # display successful msg 
                    print('[Client table updated.]\n>>> ',end='', flush = True)
                elif action == '<cf>':
                    # confirmed registration
                    print('[Welcome, You are registered.]\n>>> ', end='', flush=True)
                elif action == '<du>':
                    # duplicate username
                    print('Nickname already exists. Please try another one.')
                    os._exit(1)
                elif action == '<mg>':
                    # message received
                    sendIP = senderAddress[0]
                    sendPort = senderAddress[1]
                    # print(self.regTable.items())
                    sendName = [i for i in self.regTable.items() if i[1][0] == sendIP and i[1][1] == sendPort][0][0]
                    self.rcvMsg(sendName, modifiedMessage[4:])
                    ack = '<ak>'+self.name
                    self.clientSocket.sendto(ack.encode(), (sendIP, sendPort))
                elif action == '<ak>':
                    # message ack received
                    self.msgIsWaiting = False # stop timer
                    print('>>> [Message received by '+modifiedMessage[4:]+'.]')
                elif action == '<de>':
                    # dereg confirmation received.
                    self.derIsWaiting = False # stop timer
                    print('>>> [You are Offline. Bye.]')
                    self.status = False
                elif action == '<oc>':
                    # has offline chats
                    print('[You have messages]\n>>> ', end='')
                    self.offline_chat(modifiedMessage[4:])
                elif action == '<io>':
                    # the receiver is online
                    print('[Client '+modifiedMessage[4:]+' exists!!]')
                elif action == '<of>':
                    # offline msg received by server
                    self.serIsWaiting = False
                    print('[Messages received by the server and saved]',end='\n')
                elif action == '<rg>':
                    # server received group chat
                    self.gcIsWaiting = False
                    print('>>> [Message received by Server.]')
                elif action == '<gc>':
                    # received group chat from server
                    self.clientSocket.sendto('<z>'.encode(), (self.serverIP, self.serverPort))
                    self.rcvGroupMsg(modifiedMessage[4:])
                elif action == '<ck>':
                    # online check - reply to server
                    self.clientSocket.sendto('<k>'.encode(), (self.serverIP, self.serverPort))
            # while offline
            if not self.status:
                if action == '<re>':
                    # rereg confirmation received.
                    print('[Welcome back.]\n>>> ', end='')
                    self.status = True

    def updateTable(self, regTableStr):
        '''Overwrite current regTable'''
        for client in regTableStr.split():
            name, IP, port, status = client.split(',')
            self.regTable[name] = (IP, int(port), bool(int(status)))

    def rcvMsg(self, sendName, msg):
        '''Display the received message'''
        print(sendName+': '+msg+'\n>>> ', end='')

    def sendMsg(self, name, msg):
        '''
        Function of sending direct messages. 
        First check if the recipient is online or not.
            if online, directly send to its address and port. Expect ACK 
                if not responding, send to server as saved chat
            if offline, directly send to server. Expect ACK
                if server not responding, continue. (doesn't quit).
        '''
        if name not in self.regTable:
            print(">>> [Receiver doesn't exist!]")
        elif self.regTable[name][2] == False:
            # send msg to offline client
            # look up receiver's address
            rcvIP = self.regTable[name][0]
            rcvPort = self.regTable[name][1]
            # msg = '<m>' + ',' + rcvIP + ',' + str(rcvPort) + ',' + self.name + ',' + name + ',' + msg
            modMsg = '<m>' + ',' + self.name + ',' + name + ',' + msg
            self.clientSocket.sendto(modMsg.encode(), (self.serverIP, self.serverPort))
            # if server not responding, retry 5 times
            self.serIsWaiting = True 
            time.sleep(0.5)
            if self.serIsWaiting: # still waiting - retry for 5 times
                for _ in range(5):
                    # resend
                    self.clientSocket.sendto(msg.encode(), (self.serverIP, self.serverPort))
                    time.sleep(0.5)
                    if not self.serIsWaiting: # received by the server
                        break
                # after 5 tries - server not responding - print warning
                if self.serIsWaiting:
                    print('>>> [Server not responding]')
                    # os._exit(1) # server is down, still able to send message
        else:
            # send msg to online client
            # lookup receiver's address from regTable
            # assume no different users use the same IP and Port pair
            rcvIP = self.regTable[name][0]
            rcvPort = self.regTable[name][1]
            modMsg = '<mg>' + msg
            self.clientSocket.sendto(modMsg.encode(), (rcvIP, rcvPort))
            # set timer
            self.msgIsWaiting = True
            time.sleep(0.5)
            if self.msgIsWaiting: # still waiting - timeout
                # inform server that receiver is offline and send message
                print('>>> [No ACK from {}, message is being sent to server...]'.format(name), end='\n')
                rcvIP = self.regTable[name][0]
                rcvPort = self.regTable[name][1]
                # known bug: do not use comma ',' in the nickname.
                modMsg_off = '<f>' + ',' + self.name + ',' + name + ',' + msg
                self.clientSocket.sendto(modMsg_off.encode(), (self.serverIP, self.serverPort))
                # senario that server is also not responding:
                self.serIsWaiting = True 
                time.sleep(0.5)
                if self.serIsWaiting: # still waiting - retry for 5 times
                    for _ in range(5):
                        # resend
                        self.clientSocket.sendto(msg.encode(), (self.serverIP, self.serverPort))
                        time.sleep(0.5)
                        if not self.serIsWaiting: # received by the server
                            break
                    # after 5 tries - server not responding - print warning
                    if self.serIsWaiting:
                        print('>>>[Server not responding]')
                        # os._exit(1) # server is down but still able to send messages

    def userInput(self):
        '''
        Take the user's input and direct the action to the desired function
        '''
        while True:
            command = input('>>> ').split()
            if len(command) == 0:
                continue
            if len(command) < 2:
                print('>>> [Not enough arguments. Try again.]')
                continue

            if self.status:
                if command[0] == 'send':
                    rcvName = command[1]
                    msg = ' '.join(command[2:])
                    self.sendMsg(rcvName, msg)

                elif command[0] == 'dereg':
                    # self.status = False # for testing if timeout works
                    if len(command)!= 2:
                        print('>>> [Incorrect number of arguments.]')
                    elif command[1] != self.name:
                        print(">>> [Nickname doesn't exist or trying to dereg another client.]")
                    else:
                        msg = '<d>'+command[1]
                        self.clientSocket.sendto(msg.encode(), (self.serverIP, self.serverPort))
                        # for timeout - start timer
                        self.derIsWaiting = True 
                        time.sleep(0.5)
                        if self.derIsWaiting: # still waiting - retry for 5 times
                            for _ in range(5):
                                # resend
                                self.clientSocket.sendto(msg.encode(), (self.serverIP, self.serverPort))
                                time.sleep(0.5)
                                if not self.derIsWaiting: # received by the server
                                    break
                            # after 5 tries - server not responding - exiting...
                            if self.derIsWaiting:
                                print('>>> [Server not responding]')
                                print('>>> [Exiting]')
                                os._exit(1)


                elif command[0] == 'send_all':
                    msg = ' '.join(command[1:])
                    self.sendGroup(msg)
                    self.gcIsWaiting = True
                    time.sleep(0.5)
                    if self.gcIsWaiting: # still waiting - retry for 5 times
                        for _ in range(5):
                            self.sendGroup(msg)
                            time.sleep(0.5)
                            if not self.gcIsWaiting: # has received by the server during sleeping
                                break
                        if self.gcIsWaiting:
                            print('>>> [Server not responding]')
                            # os._exit(1) # Don't wanna exit cuz server is down but client still able to send msg
                else:
                    print('>>> [Invalid command during online]')

            elif not self.status:
                if command[0] == 'reg':
                    if len(command)!= 2:
                        print('>>> [Incorrect number of arguments.]')
                    elif command[1] != self.name:
                        print(">>> [Nickname doesn't exist or trying to reg another client.]")
                    else:
                        msg = '<g>'+command[1]
                        self.clientSocket.sendto(msg.encode(), (self.serverIP, self.serverPort))
                else:
                    print('>>> [Invalid command during offline]')

    def offline_chat(self, chats):
        '''
        Display the saved message when logging back;
        Send ack back to clear save chat cache at server
        '''
        chat = chats.split("|")
        for i in chat:
            # known bug: if save chat contains & or |, the program will crush.
            senderName, ts, msg = i.split('&')
            print(senderName + ': <' + ts + '> ' + msg + '\n>>> ', end='')
        # send ack back to server
        ack = '<o>'+self.name
        self.clientSocket.sendto(ack.encode(), (self.serverIP, self.serverPort))
    
    def sendGroup(self,msg):
        '''send group messages to server'''
        modMsg = '<c>' + msg
        self.clientSocket.sendto(modMsg.encode(), (self.serverIP, self.serverPort))

    def rcvGroupMsg(self, str):
        '''Display online group messages'''
        senderName, msg = str.split('|')
        print('Channel_Message '+senderName+': '+msg+'\n>>> ', end='')