#!/usr/bin/python3
"""Implementation of RDT3.0

functions: rdt_network_init(), rdt_socket(), rdt_bind(), rdt_peer()
           rdt_send(), rdt_recv(), rdt_close()

Student name: Wong Ka Ngai
Student No. : 3035568881
Date and version: 5/4/2021
Development platform: Windows
Python version: 3.7.0
"""

import socket
import random
import sys
import select
import struct

#some constants
PAYLOAD = 1000		#size of data payload of the RDT layer
CPORT = 100			#Client port number - Change to your port number
SPORT = 200			#Server port number - Change to your port number
TIMEOUT = 0.05		#retransmission timeout duration
TWAIT = 10*TIMEOUT 	#TimeWait duration

#store peer address info
__peeraddr = ()		#set by rdt_peer()
#define the error rates
__LOSS_RATE = 0.0	#set by rdt_network_init()
__ERR_RATE = 0.0

message_format = struct.Struct('BBHH')
HEADER = 6
send_num = 0
recv_num = 0
buffer=[]


#internal functions - being called within the module
def __udt_send(sockd, peer_addr, byte_msg):
	"""This function is for simulating packet loss or corruption in an unreliable channel.

	Input arguments: Unix socket object, peer address 2-tuple and the message
	Return  -> size of data sent, -1 on error
	Note: it does not catch any exception
	"""
	global __LOSS_RATE, __ERR_RATE
	if peer_addr == ():
		print("Socket send error: Peer address not set yet")
		return -1
	else:
		#Simulate packet loss
		drop = random.random()
		if drop < __LOSS_RATE:
			#simulate packet loss of unreliable send
			print("WARNING: udt_send: Packet lost in unreliable layer!!")
			return len(byte_msg)

		#Simulate packet corruption
		corrupt = random.random()
		if corrupt < __ERR_RATE:
			err_bytearr = bytearray(byte_msg)
			pos = random.randint(0,len(byte_msg)-1)
			val = err_bytearr[pos]
			if val > 1:
				err_bytearr[pos] -= 2
			else:
				err_bytearr[pos] = 254
			err_msg = bytes(err_bytearr)
			print("WARNING: udt_send: Packet corrupted in unreliable layer!!")
			return sockd.sendto(err_msg, peer_addr)
		else:
			return sockd.sendto(byte_msg, peer_addr)

def __udt_recv(sockd, length):
	"""Retrieve message from underlying layer

	Input arguments: Unix socket object and the max amount of data to be received
	Return  -> the received bytes message object
	Note: it does not catch any exception
	"""
	(rmsg, peer) = sockd.recvfrom(length)
	return rmsg

def __IntChksum(byte_msg):
	"""Implement the Internet Checksum algorithm

	Input argument: the bytes message object
	Return  -> 16-bit checksum value
	Note: it does not check whether the input object is a bytes object
	"""
	total = 0
	length = len(byte_msg)	#length of the byte message object
	i = 0
	while length > 1:
		total += ((byte_msg[i+1] << 8) & 0xFF00) + ((byte_msg[i]) & 0xFF)
		i += 2
		length -= 2

	if length > 0:
		total += (byte_msg[i] & 0xFF)

	while (total >> 16) > 0:
		total = (total & 0xFFFF) + (total >> 16)

	total = ~total

	return total & 0xFFFF


#These are the functions used by appliation

def rdt_network_init(drop_rate, err_rate):
	"""Application calls this function to set properties of underlying network.

    Input arguments: packet drop probability and packet corruption probability
	"""
	random.seed()
	global __LOSS_RATE, __ERR_RATE
	__LOSS_RATE = float(drop_rate)
	__ERR_RATE = float(err_rate)
	print("Drop rate:", __LOSS_RATE, "\tError rate:", __ERR_RATE)


def rdt_socket():
	"""Application calls this function to create the RDT socket.

	Null input.
	Return the Unix socket object on success, None on error

	Note: Catch any known error and report to the user.
	"""
	######## Your implementation #######
	try:
		sd = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
	except socket.error as emsg:
		print("Socket creation error: ", emsg)
		return None
	return sd


def rdt_bind(sockd, port):
	"""Application calls this function to specify the port number
	used by itself and assigns them to the RDT socket.

	Input arguments: RDT socket object and port number
	Return	-> 0 on success, -1 on error

	Note: Catch any known error and report to the user.
	"""
	######## Your implementation #######
	try:
		sockd.bind(("",port))
	except socket.error as emsg:
		print("Socket bind error: ", emsg)
		return -1
	return 0


def rdt_peer(peer_ip, port):
	"""Application calls this function to specify the IP address
	and port number used by remote peer process.

	Input arguments: peer's IP address and port number
	"""
	######## Your implementation #######
	global __peeraddr
	__peeraddr = (peer_ip, port)


def rdt_send(sockd, byte_msg):
	"""Application calls this function to transmit a message to
	the remote peer through the RDT socket.

	Input arguments: RDT socket object and the message bytes object
	Return  -> size of data sent on success, -1 on error

	Note: Make sure the data sent is not longer than the maximum PAYLOAD
	length. Catch any known error and report to the user.
	"""
	######## Your implementation #######
	global PAYLOAD, HEADER, __peeraddr, message_format, send_num, recv_num, buffer

	#Make sure the data sent is not longer than the maximum PAYLOAD length.
	if (len(byte_msg) > PAYLOAD):
		msg = byte_msg[0:PAYLOAD]
	else:
		msg = byte_msg

	checksum = __IntChksum(message_format.pack(12, send_num, 0, len(msg)) + msg)

	send_pkt = message_format.pack(12, send_num, checksum, len(msg)) + msg

	try:
		__udt_send(sockd, __peeraddr, send_pkt)
	except socket.error as emsg:
		print("Socket send error: ", emsg)
		return -1
	print("rdt_send: Sent one message of size ", len(msg))
	
	RList = [sockd]

	while True:
		# use select to wait for any incoming connection requests or
		# incoming messages or 10 seconds
		try:
			Rready, Wready, Eready = select.select(RList, [], [], TIMEOUT)
		except select.error as emsg:
			print("At select, caught an exception:", emsg)
			return -1
		except KeyboardInterrupt:
			print("At select, caught the KeyboardInterrupt")
			return -1

		# if has incoming activities
		if Rready:
			# for each socket in the READ ready list
			for sd in Rready:
				try:
					rmsg = __udt_recv(sockd, PAYLOAD+HEADER)
				except socket.error as emsg:
					print("Socket send error: ", emsg)
					return -1
				echk = __IntChksum(rmsg)
				rheader = rmsg[:HEADER]
				(rtype, rseq, rchksum, rlen) = message_format.unpack(rheader)

				if echk == 0: #not corrupted
					if rtype==11 and rseq==send_num: #correct ack
						print("rdt_send: Received the expected ACK")
						if send_num == 0: 
							send_num =1
						else: 
							send_num = 0
						#Return  -> size of data sent on success
						return len(msg)
					elif rtype==11 and rseq != send_num: #wrong ack
						print("rdt_send: Received an unexpected ACK")
					elif rtype==12:
						print("rdt_send: I am expecting an ACK packet, but received a DATA packet")
						print("rdt_send: Peer sent me a new DATA packet!!")
						print("rdt_send: Drop the packet as I cannot accept it at this point")

						if rmsg not in buffer:
							buffer.append(rmsg)

						ackchk = __IntChksum(message_format.pack(11, rseq, 0, 0))
						send_ack = message_format.pack(11, rseq, ackchk, 0)
						try:
							__udt_send(sockd, __peeraddr, send_ack)
						except socket.error as emsg:
							print("Socket send error: ", emsg)
							return -1
				else: #corrupted
					if rtype==11:
						print("rdt_send: Received a corrupted packet: Type = ACK, Length = 6")
						print("rdt_send: Drop the packet")
					else:
						print("rdt_send: Received a corrupted packet: Type = Data, Length =", rlen+6)
						print("rdt_send: Drop the packet")
		else:
			print("rdt_send: Timeout!! Retransmit the packet", send_num, "again")
			try:
				__udt_send(sockd, __peeraddr, send_pkt)
			except socket.error as emsg:
				print("Socket send error: ", emsg)
				return -1

						
def rdt_recv(sockd, length):
	"""Application calls this function to wait for a message from the
	remote peer; the caller will be blocked waiting for the arrival of
	the message. Upon receiving a message from the underlying UDT layer,
    the function returns immediately.

	Input arguments: RDT socket object and the size of the message to
	received.
	Return  -> the received bytes message object on success, b'' on error

	Note: Catch any known error and report to the user.
	"""
	######## Your implementation #######
	global PAYLOAD, HEADER, __peeraddr, message_format, send_num, recv_num, buffer
	while buffer != []:
		rmsg = buffer.pop(0)
		rheader = rmsg[:HEADER]
		(rtype, rseq, rchksum, rlen) = message_format.unpack(rheader)
		if rseq == recv_num:
			if recv_num == 0:
				recv_num = 1
			else:
				recv_num = 0
			return (rmsg[HEADER:]) #Return  -> the received bytes message object on success
	
	while True:
		try:
			rmsg = __udt_recv(sockd, length+HEADER)
		except socket.error as emsg:
			print("Socket recv error: ", emsg)
			return b''
		echk = __IntChksum(rmsg)
		rheader = rmsg[:HEADER]
		(rtype, rseq, rchksum, rlen) = message_format.unpack(rheader)
		print("rdt_recv: Received a message of size %d" % len(rmsg))

		if echk==0 and rtype ==12: #no error data packet
			if rseq==recv_num:
				print("rdt_recv: Got an expected packet")
				ackchk = __IntChksum(message_format.pack(11, rseq, 0, 0))
				send_ack = message_format.pack(11, rseq, ackchk, 0)
				try:
					__udt_send(sockd, __peeraddr, send_ack)
				except socket.error as emsg:
					print("Socket send error: ", emsg)
					return b''
				if recv_num == 0:
					recv_num = 1
				else:
					recv_num = 0
				return (rmsg[HEADER:])
			elif rseq != recv_num:
				ackchk = __IntChksum(message_format.pack(11, rseq, 0, 0))
				send_ack = message_format.pack(11, rseq, ackchk, 0)
				try:
					__udt_send(sockd, __peeraddr, send_ack)
				except socket.error as emsg:
					print("Socket send error: ", emsg)
					return b''
				print("rdt_recv: Received a retransmission DATA packet from peer!!")
				print("rdt_recv: Retransmit the ACK packet")
		
		else: #error data packet
			print("rdt_recv: Received a corrupted packet: Type =", rtype, ", Length =", len(rmsg))
			print("rdt_recv: Drop the packet")
			prevack = 1 - recv_num
			ackchk = __IntChksum(message_format.pack(11, prevack, 0, 0))
			send_ack = message_format.pack(11, prevack, ackchk, 0)
			try:
				__udt_send(sockd, __peeraddr, send_ack)
			except socket.error as emsg:
				print("Socket send error: ", emsg)
				return b''
			






def rdt_close(sockd):
	"""Application calls this function to close the RDT socket.

	Input argument: RDT socket object

	Note: (1) Catch any known error and report to the user.
	(2) Before closing the RDT socket, the reliable layer needs to wait for TWAIT
	time units before closing the socket.
	"""
	######## Your implementation #######
	RList = [sockd]
	while True:
		try:
			Rready, Wready, Eready = select.select(RList, [], [], TWAIT)
		except select.error as emsg:
			print("At select, caught an exception:", emsg)
			return -1
		except KeyboardInterrupt:
			print("At select, caught the KeyboardInterrupt")
			return -1

		if Rready:
			# for each socket in the READ ready list
			for sd in Rready:
				try:
					rmsg = __udt_recv(sockd, PAYLOAD+HEADER)
				except socket.error as emsg:
					print("Socket send error: ", emsg)
					return -1
				
				echk = __IntChksum(rmsg)
				rheader = rmsg[:HEADER]
				(rtype, rseq, rchksum, rlen) = message_format.unpack(rheader)

				if echk==0 and rtype==12: #no error data
					ackchk = __IntChksum(message_format.pack(11, rseq, 0, 0))
					send_ack = message_format.pack(11, rseq, ackchk, 0)
					try:
						__udt_send(sockd, __peeraddr, send_ack)
					except socket.error as emsg:
						print("Socket send error: ", emsg)
						return b''
		else:
			print("rdt_close: Nothing happened for 0.500 second")
			print("rdt_close: Release the socket")
			try:
				sockd.close()
			except socket.error as emsg:
				print("Socket close error: ", emsg)
			break

		
		

