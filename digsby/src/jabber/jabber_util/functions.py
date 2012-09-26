from pyxmpp.xmlextra import common_doc, COMMON_NS

def xpath_eval(node,expr,namespaces=None):
    """Evaluate an XPath expression on the stanza XML node.

    The expression will be evaluated in context where the common namespace
    (the one used for stanza elements, mapped to 'jabber:client',
    'jabber:server', etc.) is bound to prefix "ns" and other namespaces are
    bound accordingly to the `namespaces` list.

    :Parameters:
        - `expr`: XPath expression.
        - `namespaces`: mapping from namespace prefixes to URIs.
    :Types:
        - `expr`: `unicode`
        - `namespaces`: `dict` or other mapping
    """
    ctxt = common_doc.xpathNewContext() #@UndefinedVariable
    ctxt.setContextNode(node)
    ctxt.xpathRegisterNs("ns",COMMON_NS)
    if namespaces:
        for prefix,uri in namespaces.items():
            ctxt.xpathRegisterNs(unicode(prefix),uri)
    ret=ctxt.xpathEval(unicode(expr))
    ctxt.xpathFreeContext()
    return ret