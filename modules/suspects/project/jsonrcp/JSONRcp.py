'''Info Header Start
Name : JSONRcp
Author : Admin@DESKTOP-RTI312L
Version : 0
Build : 3
Savetimestamp : 2023-01-06T14:15:26.725704
Saveorigin : Project.toe
Saveversion : 2022.28040
Info Header End'''
from email import message
import json
from uuid import uuid4
import uuid

class JSONRcp:
	"""
	JSONRcp description
	"""
	def __init__(self, ownerComp):
		# The component to which this extension is attached
		self.ownerComp = ownerComp
		self.peers = {}
		self.pending_requests = {}
		self.process_requests = {}
		self.Clear_Table()
		self.Reconnect()
	
	def Reconnect(self):
		self.ownerComp.op("reconnect").par.value0.pulse(0, frames = 10)

	def Send_Request(self, method, auto_id = False, id = None, params = {}, peer = None):
		package = {
			"jsonrcp" : "2.0",
			"method"  : method
		}
		if auto_id: id = str( uuid4() )
		if params: package["params"] 	= params
		if id: 
			package["id"] 				= id 
			self.pending_requests[id]	= package
		message = json.dumps( package )
		(self.peers.get(peer, None) or self.ownerComp.op("tcpip1")).send( message )

	def Send_Response(self, id, result):
		
		prcoessing_request = self.process_requests[id]
		package = {
			"jsonrcp" 	:  "2.0",
			"id"		: id,
			"result"	: result
		}
		prcoessing_request["peer"].send( json.dumps( package) )
		del self.process_requests[id]
		
	def Send_Error(self, id, error):
		prcoessing_request = self.process_requests[id]
		package = {
			"jsonrcp" 	:  "2.0",
			"id"		: id,
			"error"		: error
		}
		prcoessing_request[id]["peer"].send( json.dumps( package) )
		del self.process_requests[id]

	def peer_id(self, peer):
		return f"{peer.address}:{peer.port}"

	def Clear_Table(self):
		self.ownerComp.op("peers").clear( keepFirstRow = True )
		self.ownerComp.op("fifo1").par.clear.pulse()
		for key, peer in self.peers.items():
		
			self.ownerComp.op("peers").appendRow(
				[self.peer_id(peer), 1, peer.hostname] 
			)

	def connect(self, peer):
		peer_id = self.peer_id(peer)
		self.peers[ peer_id ] = peer
		self.ownerComp.op("peers").appendRow( [peer_id, peer.hostname] )
		self.ownerComp.op("callbackManager").Do_Callback( "Connect", peer_id )

	def disconnect(self, peer):
		peer_id = self.peer_id(peer)
		del self.peers[peer_id]
		self.ownerComp.op("peers").deleteRow(peer_id)
		self.ownerComp.op("callbackManager").Do_Callback( "Disconnect", peer_id )

	def parse_message(self, message, peer):
		message_dict = json.loads(message)
		self.ownerComp.op("fifo1").appendRow( [ self.peer_id(peer), message])
		peer_id = self.peer_id( peer )
	
		if "method" in message_dict: 	self.handle_request( message_dict, peer_id)
		elif "result" in message_dict: 	self.handle_result( message_dict, peer_id)
		elif "error" in message_dict: 	self.handle_error( message_dict, peer_id)

	def handle_request( self, message_dict, peer_id):
		id = message_dict.get( "id", None )
		if id:
			self.process_requests[id] = {
				"message_dict" 	: message_dict,
				"peer" 			: self.peers[peer_id]
			}
		self.ownerComp.op("callbackManager").Do_Callback(
			"Request",
			message_dict["method"],
			message_dict.get( "params", None ),
			id,
			peer_id
		)
		

	def handle_result(self, message_dict, peer_id):
		self.ownerComp.op("callbackManager").Do_Callback(
			"Response",
			message_dict["result"],
			message_dict["id"],
			self.pending_requests[ message_dict["id"] ],
			peer_id
		)
		del self.pending_requests[ message_dict["id"] ]

	def handle_error(self, message_dict, peer_id):
		self.ownerComp.op("callbackManager").Do_Callback(
			"Response",
			message_dict["error"],
			message_dict["id"],
			self.pending_requests[ message_dict["id"] ],
			peer_id
		)
		del self.pending_requests[ message_dict["id"] ]