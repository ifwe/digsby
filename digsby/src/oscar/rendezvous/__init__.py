"""
Rendezvous is the subset of OSCAR that handles chat, and also peer-to-peer
operations like direct connections, file transfers, and video chats.
"""
from oscar.rendezvous.peer import handlech2
from oscar.rendezvous.directim import directconnect
from oscar.rendezvous.rendezvous import rdv_snac, rdv_types
