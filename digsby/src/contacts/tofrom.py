from common.protocolmeta import protocols
from itertools import islice

def first(iterable):
    try:
        return islice(iterable, 1).next()
    except StopIteration:
        return None

def im_service_compatible(to_service, from_service):
    '''
    Returns True if a buddy on to_service can be IMed from a connection to from_service.
    '''
    return to_service in protocols[from_service].compatible

def choose_to(metacontact):
    return metacontact.first_online

def choose_from(contact, accounts, tofrom):
    '''
    Given a contact, returns the best connected account to IM it from.

    Checks the to/from history.

    Returns an account object, or None.
    '''

    # First, check the to/from history.
    acct = lookup_tofrom_account(contact, accounts, tofrom)
    if acct is not None:
        return acct

    # If no to/from history exists for this contact, but one of 
    # the connected accounts is its owner, return that account.
    for account in accounts:
        if account.connection is contact.protocol:
            return account

    # No connected accounts actually owned the Contact. Now just
    # find a *compatible* connected account.
    return first(compatible_im_accounts(contact, accounts))

def lookup_tofrom_account(contact, connected_accounts, tofrom):
    '''
    Searches the to/from IM list for an entry matching contact, where
    the from account matching the entry must be in connected_accounts.

    Returns a matching from account, or None.
    '''
    name, service = contact.name, contact.service

    # Loop through each entry in the tofrom list
    for bname, bservice, fromname, fromservice in tofrom:
        # If the buddy matches,
        if name == bname and service == bservice:
            for acct in connected_accounts:
                # and the from account matches, return it.
                if acct.name == fromname and acct.service == fromservice:
                    return acct

def compatible_im_accounts(contact, accounts):
    '''
    Given a Contact and a sequence of Accounts, yields the accounts
    which can send IMs to the Contact.
    '''
    for account in accounts:
        to_service = contact.service
        from_service = account.protocol
        if im_service_compatible(to_service, from_service):
            yield account


