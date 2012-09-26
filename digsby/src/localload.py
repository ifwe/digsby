'''
Created on Aug 14, 2012

@author: Christopher
'''
from digsby.blobs import name_to_ns
from digsby.digsbylocal import load_local, InvalidUsername, InvalidPassword, \
    load_local_blob

def get_local_data(username, password):
    local_acct_data = load_local(username, password)
    #deal with passwords
    localblobs = {}
    blobnames = name_to_ns.keys()
    for blobname in blobnames:
        #find cache file path]
        #load file
        try:
            with open('fname', 'rb') as f:
                #assign to data
                data = f.read()
        except Exception:
            pass #fail
        try:
            data = load_local_blob(username, password)
            if data is not None:
                localblobs[blobname] = data
        except Exception:
            pass
    return {'accounts':local_acct_data, 'blobs':localblobs}

def get_remote_data(username, password):
    pass
    #launch new digsbyprotocol

    #prevent actually "going online"
    #we can also circumvent the normal blob cache routine by loading directly from data with new handlers

    #request accounts
    #request every blob
    #disconnect
