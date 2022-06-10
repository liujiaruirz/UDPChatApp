from socket import *
import os.path
from datetime import datetime
from threading import Thread
import time

class Server:
    '''
    Server object for the chat application. 
    Handle registration, de-registration, group chat, and offline chats.
    Use object variables offCheckWaiting and channelAckWaiting to determine timeouts.
    '''
    def __init__(self, port):
        # create socket instance
        self.serverSocket = socket(AF_INET, SOCK_DGRAM)
        self.serverSocket.bind(('', port))
        self.regTable = {}
        self.offline_chat_buffer = {}
        self.offCheckWaiting = False
        self.channelAckWaiting = False

        # start listening
        t_listen = Thread(target=self.listen)
        t_listen.start()

    def listen(self):
        '''
        Server socket listening function. 
        Receive requests from clients and direct the request to specific functions.
        '''
        while True:
            # read from UDP socket into message
            message, clientAddress = self.serverSocket.recvfrom(2048)
            modifiedMessage = message.decode()
            action = modifiedMessage[:3]

            if action == '<r>':
                # registration
                self.register(modifiedMessage[3:], clientAddress)

            elif action == '<d>':
                # de-reg request
                self.dereg(modifiedMessage[3:])

            elif action == '<g>':
                # re-reg request
                self.rereg(modifiedMessage[3:])

            elif action == '<m>':
                # received msg sent to offline client
                # ignore one comma in the str (modifiedMessage)
                self.offline_chat(modifiedMessage[4:], clientAddress[0], clientAddress[1])
            
            elif action == '<f>':
                # received offline msg sent to online client
                # need to change the status of the receiver to offline
                self.offline_chat(modifiedMessage[4:], clientAddress[0], clientAddress[1])

            elif action == '<o>':
                # received ack of offline chat
                # remove offline chats from the buffer
                del self.offline_chat_buffer[modifiedMessage[3:]]

            elif action == '<c>':
                # received channel message
                self.groupChat(modifiedMessage[3:], clientAddress)

    def broadcast(self):
        '''
        Broadcast the registration table to all active users.
        '''
        regTableStr = '<bc>'
        # convert clients' info to a whole str to encode
        # print(self.regTable)
        for name in self.regTable:
            regTableStr += name+','
            regTableStr += self.regTable[name][0]+','
            regTableStr += str(self.regTable[name][1])+',' # convert int to str for port
            if self.regTable[name][2]==True:
                regTableStr += str(1)+' ' # convert True to str 1 for status
            else:
                regTableStr += str(0)+' ' # convert False to str 0 for status

        # get all client addresses and broadcast the encoded table
        for name in self.regTable:
            if self.regTable[name][2] == True: # only broadcast to active users
                clientAddr = (self.regTable[name][0], self.regTable[name][1])
                self.serverSocket.sendto(regTableStr.encode(), clientAddr)
        
    def register(self, name, clientAddress):
        '''
        Register clients upon initialization.
        Reply to the client of registration the confirmation and broadcast the amended regTable to other active users.
        '''
        # regTable (dict) {[name]: IP, Port, status}
        if name in self.regTable:
            duplic = '<du>'
            self.serverSocket.sendto(duplic.encode(), clientAddress)
        else:
            self.regTable[name] = (clientAddress[0], clientAddress[1], True)
            confirmation = '<cf>'
            self.serverSocket.sendto(confirmation.encode(), clientAddress)
            self.broadcast()

    def dereg(self, name):
        '''
        De-register clients upon receiving requests.
        Reply to the client of de-reg with the confirmation.
        Change the dereg client's online status to offline and broadcast to others. 
        '''
        # handled edge case for dereg non-existed name or for another client's name in client.py
        clientAddress = (self.regTable[name][0],self.regTable[name][1])
        self.regTable[name] = (self.regTable[name][0],self.regTable[name][1],False)
        msg = '<de>'
        self.serverSocket.sendto(msg.encode(), clientAddress)
        self.broadcast()

    def rereg(self, name):  
        '''
        Re-register clients upon receiving requests.
        Reply to the client of re-reg with the confirmation.
        Note the order of re-reg and send offline chat.
        Since in offline mode, the client cannot receive other message but the re-reg confirmation. 
        So the Server needs to send <re> first.
        '''      
        # handled edge case for dereg non-existed name or for another client's name in client.py
        # no need to check again here
        # change online-status to True
        clientAddress = (self.regTable[name][0],self.regTable[name][1])
        self.regTable[name] = (self.regTable[name][0],self.regTable[name][1],True)
        msg = '<re>'
        self.serverSocket.sendto(msg.encode(), clientAddress)
        # broadcast to all active clients
        self.broadcast()

        # send offline chat if there is any
        if name in self.offline_chat_buffer:
            off_msg = '<oc>'
            for i in self.offline_chat_buffer[name]:
                off_msg += i[0]+'&'+i[1]+'&'+i[2]+'|'
            self.serverSocket.sendto(off_msg[:-1].encode(), (self.regTable[name][0], self.regTable[name][1]))

    def offline_chat(self, str, senderIP, senderPort, Group=False):
        '''
        Handles offline direct chats and offline group chat.
        Check if the recipient client is really online:
            1. if the recipient client is offline at the server's end, save chat
            2. if the recipient client is online at the server's end, request ACK from recipient client:
                    if timeout, switch the recipient to offline, save chat, and broadcast
                    otherwise, reply to the sender warning and broadcast
        Saved chats format: dict of list of vectors:
        {name of recipient clients: [(name of sender, timestamp, message), ...]}
        '''

        senderName, rcvName = str.split(',')[:2]

        # for direct offline chat, check if the receiver is really offline
        # if online, send warning to sender
        if not Group:
            # send confirmation to receiver
            if self.regTable[rcvName][2]:
                # if receiver online at server's end - expect ack to check
                rcvIP = self.regTable[rcvName][0]
                rcvPort = self.regTable[rcvName][1]
                self.serverSocket.sendto('ck'.encode(), (rcvIP, rcvPort))
                # start timer
                self.offCheckWaiting = True
                t_offCheck = Thread(target=self.offCheck_receiver)
                t_offCheck.start()
                time.sleep(0.5)
                if self.offCheckWaiting: # still waiting - no more retries (we don't wanna try 5 times cuz client would timeout!)
                    # for _ in range(5):
                    #     # resend
                    #     self.serverSocket.sendto('ck'.encode(), (rcvIP, rcvPort))
                    #     time.sleep(0.5)
                    #     if not self.offCheckWaiting: # received by the server
                    #         break
                    # # after 5 tries - receiver not responding - change it to offline
                    # if self.offCheckWaiting:
                        self.regTable[rcvName] = (self.regTable[rcvName][0],self.regTable[rcvName][1],False)
                        self.broadcast()
                if not self.offCheckWaiting: # no longer waiting - receiver is online - inform sender
                    self.broadcast()
                    ack = '<io>'+rcvName
                    self.serverSocket.sendto(ack.encode(), (senderIP, senderPort))
                    # update sender's table
                    return
            
        # updated status. check again
        if not self.regTable[rcvName][2]: # receiver is offline at server's end - save message
            msg = ",".join(str.split(',')[2:])
            # write msg to a file
            # save_path = './'
            # clientFileName = os.path.join(save_path, rcvName+".txt")  
            # clientFile= open(clientFileName, "w")
            # clientFile.write(senderName+':'+msg)
            # clientFile.close()
            now = datetime.now()
            current_time = now.strftime("%H:%M:%S")
            if rcvName in self.offline_chat_buffer:
                self.offline_chat_buffer[rcvName].append((senderName,current_time, msg))
            else:
                self.offline_chat_buffer[rcvName] = []
                self.offline_chat_buffer[rcvName].append((senderName, current_time, msg))
            # print(self.offline_chat_buffer)
            
            if not Group: # reply to the sender in single offline chat mode
                self.serverSocket.sendto('<of>'.encode(), (senderIP, senderPort))
    
    def offCheck_receiver(self):
        '''
        Receive ACK from the target client to check if it is truly offline. If received, change global variable and stop timer.
        '''
        encMsg = self.serverSocket.recvfrom(2048)[0]
        Msg = encMsg.decode()
        action = Msg[:3]
        if action == '<k>':
            self.offCheckWaiting = False

    def groupChat(self, msg, senderAdd):
        '''
        Receives the group chat and broadcast the message to all active users. 
        For offline clients, save the message.
        '''
        # reply ack to the client
        self.serverSocket.sendto('<rg>'.encode(), senderAdd)
        # send to all active clients
        # first lookup the sender's name
        senderName = [i for i in self.regTable.items() if i[1][0] == senderAdd[0] and i[1][1] == senderAdd[1]][0][0]
        modMsg = '<gc>'+senderName+'|'+msg
        for name in self.regTable:
            if name != senderName:
                if self.regTable[name][2]: # only send to active users
                    clientAddr = (self.regTable[name][0], self.regTable[name][1])
                    self.serverSocket.sendto(modMsg.encode(), clientAddr)
                    # channel msg sent. expecting ack
                    # start timer
                    self.channelAckWaiting = True
                    t_channelack = Thread(target=self.channelack_receiver)
                    t_channelack.start()
                    time.sleep(0.5)
                    if self.channelAckWaiting: # still waiting - timeout
                        self.regTable[name] = (self.regTable[name][0],self.regTable[name][1],False)
                        self.broadcast()
                if not self.regTable[name][2]:
                    # for offline users, save chat
                    str = 'Channel_Message '+ senderName+','+name+','+msg
                    self.offline_chat(str, senderAdd[0], senderAdd[1], Group=True)

    def channelack_receiver(self):
        '''
        Receive ACK from the target client to check if it receives the group message. If received, change global variable and stop timer.
        '''
        encMsg = self.serverSocket.recvfrom(2048)[0]
        Msg = encMsg.decode()
        action = Msg[:3]
        if action == '<z>':
            self.channelAckWaiting = False