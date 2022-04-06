#!/usr/bin/python3
"""Implementation of RDT4.0

functions: rdt_network_init, rdt_socket(), rdt_bind(), rdt_peer()
           rdt_send(), rdt_recv(), rdt_close()

Student name: Wong Ka Ngai
Student No. : 3035568881
Date and version: 30/4/2021 version2.0 update based on rdt 3.0
Development platform: Windows
Python version: 3.7.0
"""

import socket
import random
import sys
import select
import struct
import math

#some constants
PAYLOAD = 1000		#size of data payload of each packet
CPORT = 100			#Client port number - Change to your port number
SPORT = 200			#Server port number - Change to your port number
TIMEOUT = 0.05		#retransmission timeout duration
TWAIT = 10*TIMEOUT 	#TimeWait duration

#store peer address info
__peeraddr = ()		#set by rdt_peer()
#define the error rates and window size
__LOSS_RATE = 0.0	#set by rdt_network_init()
__ERR_RATE = 0.0
__W = 1

message_format = struct.Struct('BBHH')
HEADER = 6
next_num = 0
expect_num = 0
base_num = 0
buffer=[]
N = 1

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

def rdt_network_init(drop_rate, err_rate, W):
	"""Application calls this function to set properties of underlying network.

    Input arguments: packet drop probability, packet corruption probability and Window size
	"""
	random.seed()
	global __LOSS_RATE, __ERR_RATE, __W
	__LOSS_RATE = float(drop_rate)
	__ERR_RATE = float(err_rate)
	__W = int(W)
	print("Drop rate:", __LOSS_RATE, "\tError rate:", __ERR_RATE, "\tWindow size:", __W)

def rdt_socket():
	"""Application calls this function to create the RDT socket.

	Null input.
	Return the Unix socket object on success, None on error

	Note: Catch any known error and report to the user.
	"""
	######## Your implementation #######
	#reuse Part 2 implementation
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
	#reuse Part 2 implementation
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
	#reuse Part 2 implementation
	global __peeraddr
	__peeraddr = (peer_ip, port)

def rdt_send(sockd, byte_msg):
	"""Application calls this function to transmit a message (up to
	W * PAYLOAD bytes) to the remote peer through the RDT socket.

	Input arguments: RDT socket object and the message bytes object
	Return  -> size of data sent on success, -1 on error

	Note: (1) This function will return only when it knows that the
	whole message has been successfully delivered to remote process.
	(2) Catch any known error and report to the user.
	"""
	######## Your implementation #######
	global PAYLOAD, HEADER, __peeraddr, message_format, next_num, expect_num, base_num, buffer, N

	#determines how many packets (N) it is going to be transmitted
	N = -(-len(byte_msg) // PAYLOAD)  #upside-down floor division= ceiling division
	total_size = len(byte_msg)

	send_pkt = [1] * N
	pointer = 0 # pointing to the first unacked packet
	base_num = next_num

	for i in range(N):
		#Make sure the data sent is not longer than the maximum PAYLOAD length.
		if (len(byte_msg) > PAYLOAD):
			msg = byte_msg[0:PAYLOAD]
			byte_msg = byte_msg[PAYLOAD:]
		else:
			msg = byte_msg
			byte_msg = None

		checksum = __IntChksum(message_format.pack(12, next_num, 0, len(msg)) + msg)

		send_pkt[i] = message_format.pack(12, next_num, checksum, len(msg)) + msg

		try:
			__udt_send(sockd, __peeraddr, send_pkt[i])
		except socket.error as emsg:
			print("Socket send error: ", emsg)
			return -1


		#increment the next sequence number, if the next is 256, back to 0
		next_num = (next_num+1)%256

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
					rmsg = __udt_recv(sd, PAYLOAD+HEADER)
				except socket.error as emsg:
					print("Socket send error: ", emsg)
					return -1
				echk = __IntChksum(rmsg)
				rheader = rmsg[:HEADER]
				(rtype, rseq, rchksum, rlen) = message_format.unpack(rheader)

				if echk == 0: #not corrupted


					if rtype==11:
						last = (base_num + N -1)%256
						if last < base_num: #reach the 255 limit, need go back to 0, base number is at 2xx but the last is at 0-9, i.e. last is smaller than base
							#it is an ack and within range, but not the last ack
							if base_num <= rseq <=255 or 0 <= rseq <= last-1:
								print("rdt_send: Received the ACK with seqNo.:",rseq)
								print("rdt_send: All segments from",base_num," to",rseq," are acknowledged")
								pointer = max((rseq - base_num +256)%256 + 1, pointer)
							#it is the last ack within range
							elif rseq==last:
								print("rdt_send: Received the ACK with seqNo.:",rseq)
								print("rdt_send: All segments from",base_num," to",rseq," are acknowledged")
								print("rdt_send: Sent",N,"messages of total size", total_size)
								return total_size
							#it is an ack but out of range
							else: 
								print("rdt_send: Received an out of range ACK with seqNo.:",rseq)
						
						else: #normal case
							#it is an ack and within range, but not the last ack
							if base_num <= rseq <= last-1:
								print("rdt_send: Received the ACK with seqNo.:",rseq)
								print("rdt_send: All segments from",base_num," to",rseq," are acknowledged")
								pointer = max((rseq - base_num +256)%256 + 1, pointer)
							elif rseq==last:
								print("rdt_send: Received the ACK with seqNo.:",rseq)
								print("rdt_send: All segments from",base_num," to",rseq," are acknowledged")
								print("rdt_send: Sent",N,"messages of total size", total_size)
								return total_size
							#it is an ack but out of range
							else: 
								print("rdt_send: Received an out of range ACK with seqNo.:",rseq)

					elif rtype==12:
						print("rdt_send: I am expecting an ACK packet, but received a DATA packet")
						print("rdt_send: Peer sent me a new DATA packet!!")
						print("rdt_send: Drop the packet as I cannot accept it at this point")
						if rseq==expect_num:
							if rmsg not in buffer:
								buffer.append(rmsg)

							ackchk = __IntChksum(message_format.pack(11, rseq, 0, 0))
							send_ack = message_format.pack(11, rseq, ackchk, 0)
							try:
								__udt_send(sockd, __peeraddr, send_ack)
							except socket.error as emsg:
								print("Socket send error: ", emsg)
								return -1
						else:
							prev_expect = (expect_num-1+256)%256
							ackchk = __IntChksum(message_format.pack(11, prev_expect, 0, 0))
							send_ack = message_format.pack(11, rseq, ackchk, 0)
							try:
								__udt_send(sockd, __peeraddr, send_ack)
							except socket.error as emsg:
								print("Socket send error: ", emsg)
								return -1

				else: #corrupted
					print("rdt_recv: Received a corrupted packet: Type =", rtype, ", Length =", len(rmsg))
					print("rdt_recv: Drop the packet")
		else:
			for i in range(pointer, N):
				print("rdt_send: Timeout!! Retransmit the packet", i, "again")
				try:
					__udt_send(sockd, __peeraddr, send_pkt[i])
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
	global PAYLOAD, HEADER, __peeraddr, message_format, next_num, expect_num, base_num, buffer, N
	while buffer != []:
		rmsg = buffer.pop(0)
		rheader = rmsg[:HEADER]
		(rtype, rseq, rchksum, rlen) = message_format.unpack(rheader)
		if rseq == expect_num:
			expect_num = (expect_num + 1 +256)%256
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
		

		if echk==0 and rtype ==12: #no error data packet
			if rseq==expect_num:
				print("rdt_recv: Got an expected packet - seqNo.:",rseq)
				print("rdt_recv: Received a message of size %d" % len(rmsg))
				ackchk = __IntChksum(message_format.pack(11, rseq, 0, 0))
				send_ack = message_format.pack(11, rseq, ackchk, 0)
				try:
					__udt_send(sockd, __peeraddr, send_ack)
				except socket.error as emsg:
					print("Socket send error: ", emsg)
					return b''
				expect_num = (expect_num + 1 +256)%256
				return (rmsg[HEADER:])

			elif rseq != expect_num:
				
				prev_expect = (expect_num-1+256)%256
				print("rdt_recv: Received a retransmission DATA packet -seqNo.: %d (expected: %d)" % (prev_expect, expect_num))
				ackchk = __IntChksum(message_format.pack(11, prev_expect, 0, 0))
				send_ack = message_format.pack(11, prev_expect, ackchk, 0)
				try:
					__udt_send(sockd, __peeraddr, send_ack)
				except socket.error as emsg:
					print("Socket send error: ", emsg)
					return b''
				print("rdt_recv: Drop the packet")
				print("rdt_recv: Retransmit the ACK packet")
				
		else: #error data packet
			print("rdt_recv: Received a corrupted packet: Type =", rtype, ", Length =", len(rmsg))
			print("rdt_recv: Drop the packet")

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
					rmsg = __udt_recv(sd, PAYLOAD+HEADER)
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

