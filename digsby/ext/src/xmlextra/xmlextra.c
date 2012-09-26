#include <Python.h>
#include <libxml/parser.h>
#include <libxml/tree.h>
#include <libxml/SAX.h>
#include <libxml/xmlerror.h>
#include <stdio.h>

static PyObject *MyError;

/*
 * Code borrowed from libxml2 python bindings
 * Copyright (C) 1998-2002 Daniel Veillard.  All Rights Reserved.
 * (see Copyright-libxml2 for copyright details)
 */

#define PyxmlNode_Get(v) (((v) == Py_None) ? NULL : \
	(((PyxmlNode_Object *)(v))->obj))
	
typedef struct {
    PyObject_HEAD
    xmlNodePtr obj;
} PyxmlNode_Object;

PyObject * libxml_xmlDocPtrWrap(xmlDocPtr doc) {
    PyObject *ret;

#ifdef DEBUG
    printf("libxml_xmlDocPtrWrap: doc = %p\n", doc);
#endif
    if (doc == NULL) {
        Py_INCREF(Py_None);
        return (Py_None);
    }
    /* TODO: look at deallocation */
    ret =
        PyCObject_FromVoidPtrAndDesc((void *) doc, (char *) "xmlDocPtr",
                                     NULL);
    return (ret);
}

PyObject * libxml_xmlNodePtrWrap(xmlNodePtr node) {
    PyObject *ret;

#ifdef DEBUG
    printf("libxml_xmlNodePtrWrap: node = %p\n", node);
#endif
    if (node == NULL) {
        Py_INCREF(Py_None);
        return (Py_None);
    }
    ret =
        PyCObject_FromVoidPtrAndDesc((void *) node, (char *) "xmlNodePtr",
                                     NULL);
    return (ret);
}

/*
 * End of code borrowed from libxml2
 */

/* Tree manipulation functions */

static PyObject * remove_ns(ATTRIBUTE_UNUSED PyObject *self, PyObject *args) {
PyObject *pyobj_tree,*pyobj_ns;
xmlNsPtr nsDef,prev;
xmlNodePtr node;
xmlNodePtr declNode = NULL;
xmlAttrPtr attr;
xmlNodePtr tree;
xmlNsPtr ns;

	if (!PyArg_ParseTuple(args, "OO", &pyobj_tree,&pyobj_ns)) return NULL;
	tree = (xmlNodePtr) PyxmlNode_Get(pyobj_tree);
	ns = (xmlNsPtr) PyxmlNode_Get(pyobj_ns);
	node = tree;
	
	if (ns == NULL) {
		PyErr_SetString(MyError,"remove_ns: NULL namespace");
		return NULL;
	}
	
	while (node != NULL) {
		/*
		 * Check if the namespace is in use by the node
		 */
		if (node->ns == ns) {
			PyErr_SetString(MyError,"remove_ns: NULL namespace");
			return NULL;
		}

		/*
		 * now check for namespace hold by attributes on the node.
		 */
		attr = node->properties;
		while (attr != NULL) {
			if (attr->ns == ns) {
				PyErr_SetString(MyError,"remove_ns: NULL namespace");
				return NULL;
			}
			attr = attr->next;
		}

		/*
		 * Check if the namespace is declared in the node
		 */
		nsDef=node->nsDef;
		while(nsDef != NULL) {
			if (nsDef == ns) {
				declNode = node;
				break;
			}
			nsDef=nsDef->next;
		}

		/*
		 * Browse the full subtree, deep first
		 */
		if (node->children != NULL) {
			/* deep first */
			node = node->children;
		} else if ((node != tree) && (node->next != NULL)) {
			/* then siblings */
			node = node->next;
		} else if (node != tree) {
			/* go up to parents->next if needed */
			while (node != tree) {
				if (node->parent != NULL)
					node = node->parent;
				if ((node != tree) && (node->next != NULL)) {
					node = node->next;
					break;
				}
				if (node->parent == NULL) {
				    node = NULL;
				    break;
				}
			}
			/* exit condition */
			if (node == tree) node = NULL;
		} else break;
		if (node == tree) break; /* should not happen... but happens somehow */
	}

	/* there is no such namespace declared here */
	if (declNode == NULL) {
		Py_INCREF(Py_None);
		return Py_None;
	}

	prev=NULL;
	nsDef=declNode->nsDef;
	while(nsDef != NULL) {
		if (nsDef == ns) {
			if (prev == NULL) declNode->nsDef=nsDef->next;
			else prev->next=nsDef->next;
			xmlFreeNs(ns);
			break;
		}
		prev=nsDef;
		nsDef=nsDef->next;
	}

	Py_INCREF(Py_None);
	return Py_None;
}

static PyObject * replace_ns(ATTRIBUTE_UNUSED PyObject *self, PyObject *args) {
PyObject *pyobj_tree,*pyobj_old_ns,*pyobj_new_ns;
xmlNodePtr tree,node;
xmlAttrPtr attr;
xmlNsPtr new_ns,old_ns;
xmlNsPtr nsDef;

	if (!PyArg_ParseTuple(args, "OOO", &pyobj_tree,&pyobj_old_ns,&pyobj_new_ns)) return NULL;
	tree = (xmlNodePtr) PyxmlNode_Get(pyobj_tree);
	old_ns = (xmlNsPtr) PyxmlNode_Get(pyobj_old_ns);
	new_ns = (xmlNsPtr) PyxmlNode_Get(pyobj_new_ns);
	node = tree;

	while (node != NULL) {

		/* 
		 * If old_ns is None and default namespace is redefined here, then skip this node and its children.
		 */
		if (old_ns == NULL) {
			nsDef=node->nsDef;
			while(nsDef != NULL) {
				if (nsDef->prefix == NULL) break;
				nsDef=nsDef->next;
			}
			if (nsDef != NULL) {
				node = node->next;
				continue;
			}
		}
		
		/*
		 * Check if the namespace is in use by the node
		 */
		if (node->ns == old_ns) {
			node->ns = new_ns;
		}

		/*
		 * now check for namespace hold by attributes on the node.
		 */
		attr = node->properties;
		while (attr != NULL) {
			if (attr->ns == old_ns) {
				node->ns = new_ns;
			}
			attr = attr->next;
		}

		/*
		 * Browse the full subtree, deep first
		 */
		if (node->children != NULL) {
			/* deep first */
			node = node->children;
		} else if ((node != tree) && (node->next != NULL)) {
			/* then siblings */
			node = node->next;
		} else if (node != tree) {
			/* go up to parents->next if needed */
			while (node != tree) {
				if (node->parent != NULL) node = node->parent;
				if ((node != tree) && (node->next != NULL)) {
					node = node->next;
					break;
				}
				if (node->parent == NULL) {
					node = NULL;
					break;
				}
			}
			/* exit condition */
			if (node == tree) node = NULL;
		} else break;
		if (node == tree) break; /* should not happen... but happens somehow */
	}
	
	Py_INCREF(Py_None);
	return Py_None;
}

/*
 * Stream reader functions 
 */

#if 1
/*
 * SAX-based stream reader 
 */

staticforward PyTypeObject SaxReaderType;

typedef struct _sax_reader{
   	PyObject_HEAD

	xmlParserCtxtPtr	ctxt;
	xmlSAXHandler		sax;
	
	startElementSAXFunc	startElement;
	endElementSAXFunc	endElement;
	charactersSAXFunc	characters;
	cdataBlockSAXFunc	cdataBlock;
	processingInstructionSAXFunc processingInstruction;
	
	errorSAXFunc		error;
	fatalErrorSAXFunc	fatalError;

	warningSAXFunc          warning;

	PyObject		*handler;
	
	int			eof;
	int			exception;
}SaxReaderObject;

void myStartElement(void *ctx,const xmlChar *name,const xmlChar **atts){
xmlParserCtxtPtr ctxt=(xmlParserCtxtPtr) ctx;
SaxReaderObject *reader=(SaxReaderObject *)ctxt->_private;
PyObject *obj;

	reader->startElement(ctx,name,atts);
	if (ctxt->nodeNr==1){
		obj=PyObject_CallMethod(reader->handler,"_stream_start","O",
					libxml_xmlDocPtrWrap(ctxt->myDoc));
		if (obj==NULL) reader->exception=1;
		else Py_DECREF(obj);
	}
	else if (ctxt->nodeNr==2){
		/*obj=PyObject_CallMethod(reader->handler,"_stanza_start","OO",
					libxml_xmlDocPtrWrap(ctxt->myDoc),
					libxml_xmlNodePtrWrap(ctxt->node));
		if (obj==NULL) reader->exception=1;
		else Py_DECREF(obj);*/
	}
}

void myEndElement(void *ctx,const xmlChar *name){
xmlParserCtxtPtr ctxt=(xmlParserCtxtPtr) ctx;
SaxReaderObject *reader=(SaxReaderObject *)ctxt->_private;
PyObject *obj;
xmlNodePtr node;

	node=ctxt->node;
	reader->endElement(ctx,name);
	if (ctxt->nodeNr==0){
		reader->eof=1;
		obj=PyObject_CallMethod(reader->handler,"_stream_end","O",
					libxml_xmlDocPtrWrap(ctxt->myDoc));
		if (obj==NULL) reader->exception=1;
		else Py_DECREF(obj);
	}
	else if (ctxt->nodeNr==1 && node){
		obj=PyObject_CallMethod(reader->handler,"_stanza","OO",
					libxml_xmlDocPtrWrap(ctxt->myDoc),
					libxml_xmlNodePtrWrap(node));
		if (obj==NULL) reader->exception=1;
		else Py_DECREF(obj);
		xmlUnlinkNode(node);
		xmlFreeNode(node);
	}
}

void myCharacters(void *ctx,const xmlChar *ch,int len){
xmlParserCtxtPtr ctxt=(xmlParserCtxtPtr) ctx;
SaxReaderObject *reader=(SaxReaderObject *)ctxt->_private;

	if (ctxt->nodeNr>1){
		reader->characters(ctx,ch,len);
	}
}

void myCdataBlock(void *ctx,const xmlChar *value,int len){
xmlParserCtxtPtr ctxt=(xmlParserCtxtPtr) ctx;
SaxReaderObject *reader=(SaxReaderObject *)ctxt->_private;

	if (ctxt->nodeNr>1){
		reader->cdataBlock(ctx,value,len);
	}
}

void myProcessingInstruction(void *ctx,const xmlChar *target,const xmlChar *data){
xmlParserCtxtPtr ctxt=(xmlParserCtxtPtr) ctx;
SaxReaderObject *reader=(SaxReaderObject *)ctxt->_private;

	if (ctxt->nodeNr==0){
		reader->processingInstruction(ctx,target,data);
	}
}

static void myError(void *ctx, const char *msg, ...){
va_list vargs;
xmlParserCtxtPtr ctxt=(xmlParserCtxtPtr) ctx;
SaxReaderObject *reader=(SaxReaderObject *)ctxt->_private;
PyObject *str,*obj;

	va_start (vargs, msg);
	str=PyString_FromFormatV(msg,vargs);
	va_end (vargs);
	if (str==NULL) {
		reader->exception=1;
		return;
	}
	obj=PyObject_CallMethod(reader->handler,"error","O",str);
	Py_DECREF(str);
	if (obj==NULL) reader->exception=1;
	else Py_DECREF(obj);
}

static void myFatalError(void *ctx, const char *msg, ...){
va_list vargs;
xmlParserCtxtPtr ctxt=(xmlParserCtxtPtr) ctx;
SaxReaderObject *reader=(SaxReaderObject *)ctxt->_private;
PyObject *str,*obj;

	va_start (vargs, msg);
	str=PyString_FromFormatV(msg,vargs);
	va_end (vargs);
	if (str==NULL) {
		reader->exception=1;
		return;
	}
	obj=PyObject_CallMethod(reader->handler,"error","O",str);
	Py_DECREF(str);
	if (obj==NULL) reader->exception=1;
	else Py_DECREF(obj);
}

static void myWarning(void *ctx, const char *msg, ...){
va_list vargs;
xmlParserCtxtPtr ctxt=(xmlParserCtxtPtr) ctx;
SaxReaderObject *reader=(SaxReaderObject *)ctxt->_private;
PyObject *str,*obj;

	va_start (vargs, msg);
	str=PyString_FromFormatV(msg,vargs);
	va_end (vargs);
	if (str==NULL) {
		reader->exception=1;
		return;
	}
	obj=PyObject_CallMethod(reader->handler,"warning","O",str);
	Py_DECREF(str);
	if (obj==NULL) reader->exception=1;
	else Py_DECREF(obj);
}

static PyObject * sax_reader_new(ATTRIBUTE_UNUSED PyObject *self, PyObject *args) {
SaxReaderObject *reader;
PyObject *handler;

	if (!PyArg_ParseTuple(args, "O", &handler)) return NULL;
	
	reader=PyObject_New(SaxReaderObject,&SaxReaderType);
	if (reader==NULL) return NULL;

	memcpy(&reader->sax,&xmlDefaultSAXHandler,sizeof(xmlSAXHandler));

	/* custom handlers */
	reader->startElement=reader->sax.startElement;
	reader->sax.startElement=myStartElement;
	reader->endElement=reader->sax.endElement;
	reader->sax.endElement=myEndElement;
	reader->error=reader->sax.error;
	reader->sax.error=myError;
	reader->fatalError=reader->sax.fatalError;
	reader->sax.fatalError=myFatalError;
	reader->warning=reader->sax.warning;
	reader->sax.warning=myWarning;
	
	/* things processed only at specific levels */
	reader->characters=reader->sax.characters;
	reader->sax.characters=myCharacters;
	reader->cdataBlock=reader->sax.cdataBlock;
	reader->sax.cdataBlock=myCdataBlock;
	reader->processingInstruction=reader->sax.processingInstruction;
	reader->sax.processingInstruction=myProcessingInstruction;

	/* unused in XMPP */
	reader->sax.resolveEntity=NULL;
	reader->sax.getEntity=NULL;
	reader->sax.entityDecl=NULL;
	reader->sax.notationDecl=NULL;
	reader->sax.attributeDecl=NULL;
	reader->sax.elementDecl=NULL;
	reader->sax.unparsedEntityDecl=NULL;
	reader->sax.comment=NULL;
	reader->sax.externalSubset=NULL;
	
	reader->eof=0;
	reader->exception=0;
	reader->handler=handler;
	Py_INCREF(handler);
	
	reader->ctxt=xmlCreatePushParserCtxt(&reader->sax,NULL,"",0,"test.xml");
	reader->ctxt->_private=reader;
	
	return (PyObject *)reader;
}

static void sax_reader_free(PyObject *self) {
SaxReaderObject *reader=(SaxReaderObject *)self;

	xmlFreeDoc(reader->ctxt->myDoc);
	reader->ctxt->myDoc = NULL;
	xmlFreeParserCtxt(reader->ctxt);
	Py_DECREF(reader->handler);
	PyObject_Del(self);
}

static PyObject * sax_reader_feed(PyObject *self, PyObject *args) {
SaxReaderObject *reader=(SaxReaderObject *)self;
char *str;
int len;
int ret;

	if (!PyArg_ParseTuple(args, "s#", &str, &len)) return NULL;

	reader->exception=0;

	ret=xmlParseChunk(reader->ctxt,str,len,len==0);

	if (reader->exception) return NULL;
	
	if (ret==0){	
		return Py_BuildValue("i", 0);
		/* Py_INCREF(Py_None);
		return Py_None; */
	}

	PyErr_Format(MyError,"Parser error #%d.",ret);
	return NULL;
}

static PyObject * sax_reader_doc(PyObject *self, PyObject *args) {
	Py_INCREF(Py_None);
	return Py_None;
}

static PyMethodDef sax_reader_methods[] = {
	{(char *)"feed", sax_reader_feed, METH_VARARGS, NULL},
	{(char *)"doc", sax_reader_doc, METH_VARARGS, NULL},
	{NULL, NULL, 0, NULL}
};

static PyObject * sax_reader_getattr(PyObject *obj, char *name) {
SaxReaderObject *reader=(SaxReaderObject *)obj;

	return Py_FindMethod(sax_reader_methods, (PyObject *)reader, name);
}
 
static int sax_reader_setattr(PyObject *obj, char *name, PyObject *v) {
	(void)PyErr_Format(PyExc_RuntimeError, "Read-only attribute: \%s", name);
	return -1;
}

static PyTypeObject SaxReaderType = {
	PyObject_HEAD_INIT(NULL)
	0,
	"_Reader",
	sizeof(SaxReaderObject),
	0,
	sax_reader_free, /*tp_dealloc*/
	0,          /*tp_print*/
	sax_reader_getattr, /*tp_getattr*/
	sax_reader_setattr, /*tp_setattr*/
	0,          /*tp_compare*/
	0,          /*tp_repr*/
	0,          /*tp_as_number*/
	0,          /*tp_as_sequence*/
	0,          /*tp_as_mapping*/
	0,          /*tp_hash */
};
#else

/*
 * Preparsing stream reader 
 */

staticforward PyTypeObject PreparsingReaderType;

/* stream lexical state */
typedef enum {
	LS_OUTER=0,	/* outside of a tag */

	LS_TSTART,	/* start tag/end tag/comment/pi/CDATA start */
	
	/* basic start tag content */
	LS_TCONT,	/* tag content */
	LS_TSLASH,	/* slash in tag (may be empty element) */
	LS_TQVAL,	/* quoted value in a tag content */

	/* CDATA in a start tag tag */	
	LS_TCDATASTART1, /* '<' */
	LS_TCDATASTART2, /* '<!' */
	LS_TCDATASTART3, /* '<![' */
	LS_TCDATASTART4, /* '<![C' */
	LS_TCDATASTART5, /* '<![CD' */
	LS_TCDATASTART6, /* '<![CDA' */
	LS_TCDATASTART7, /* '<![CDAT' */
	LS_TCDATASTART8, /* '<![CDATA' */
	LS_TCDATA,	/* escaped CDATA */
	LS_TCDATAEND1, 	/* ']' */
	LS_TCDATAEND2, 	/* ']]' */
	LS_TCDATAEND3, 	/* ']]!' */
	
	/* end tag */
	LS_ETCONT,	/* end tag content */

	/* processing instructions */
	LS_PI, 		/* content of PI */
	LS_PIEND,	/* '?' found in PI */

	/* comments/definitions */
	LS_DSTART,	/* <! */
	
	/* comments */
	LS_CSTART,	/* <!- */
	LS_COMMENT,	/* inside a comment */
	LS_COMMENTEND1,	/* "-" found in a comment */
	LS_COMMENTEND2,	/* "--" found in a comment */

	/* CDATA */	
	LS_CDATASTART3, /* '<![' */
	LS_CDATASTART4, /* '<![C' */
	LS_CDATASTART5, /* '<![CD' */
	LS_CDATASTART6, /* '<![CDA' */
	LS_CDATASTART7, /* '<![CDAT' */
	LS_CDATASTART8, /* '<![CDATA' */
	LS_CDATA,	/* escaped CDATA */
	LS_CDATAEND1, 	/* ']' */
	LS_CDATAEND2, 	/* ']]' */
	LS_CDATAEND3, 	/* ']]!' */
}LexicalState;

typedef enum {
	MT_NONE_YET=0,
	MT_IGNORE,
	MT_CDATA,
	MT_START_TAG,
	MT_END_TAG,
	MT_EMPTY_ELEMENT,
	MT_ERROR
}MarkupType;

typedef struct _preparsing_reader{
   	PyObject_HEAD

	int	depth;
	char *	buffer;
	size_t	buffer_len;
	size_t 	buffer_end;
	size_t 	buffer_pos;
	LexicalState lex_state;
	char	lex_quote;
	
	char *  document_start;
	size_t  document_start_len;
	char *  current_stanza;
	size_t  current_stanza_len;
	size_t  current_stanza_end;
	
	PyObject	*handler;
	xmlDocPtr 	doc;
	int		eof;
	int		exception;
}PreparsingReaderObject;

#if 0
#define STREAM_DEBUG
#endif

static PyObject * preparsing_reader_new(ATTRIBUTE_UNUSED PyObject *self, PyObject *args) {
PreparsingReaderObject *reader;
PyObject *handler;

	if (!PyArg_ParseTuple(args, "O", &handler)) return NULL;
	
	reader=PyObject_New(PreparsingReaderObject,&PreparsingReaderType);
	if (reader==NULL) return NULL;

	reader->depth=0;
	reader->buffer=PyMem_New(char,1024);
	if (reader->buffer==NULL) return NULL;
	reader->lex_state=LS_OUTER;
	reader->buffer_len=1024;
	reader->buffer_pos=0;
	reader->buffer_end=0;
	reader->document_start=NULL;
	reader->document_start_len=0;
	reader->current_stanza=NULL;
	reader->current_stanza_len=0;
	reader->current_stanza_end=0;
	reader->doc=NULL;
	reader->eof=0;
	reader->exception=0;
	reader->handler=handler;
	Py_INCREF(handler);
	
	return (PyObject *)reader;
}

static void preparsing_reader_clear(PreparsingReaderObject *reader) {

	PyMem_Del(reader->buffer);
	reader->buffer=NULL;
	PyMem_Del(reader->document_start);
	reader->document_start=NULL;
	PyMem_Del(reader->current_stanza);
	if (reader->doc) {
		xmlFreeDoc(reader->doc);
		reader->doc=NULL;
	}
	reader->current_stanza=NULL;
	reader->depth=0;
	reader->lex_state=LS_OUTER;
	reader->buffer_len=0;
	reader->buffer_pos=0;
	reader->buffer_end=0;
	reader->document_start=NULL;
	reader->document_start_len=0;
	reader->current_stanza=NULL;
	reader->current_stanza_len=0;
	reader->current_stanza_end=0;
	reader->doc=NULL;
	reader->eof=0;
	reader->exception=0;
}

static void preparsing_reader_free(PyObject *self) {
PreparsingReaderObject *reader=(PreparsingReaderObject *)self;

	preparsing_reader_clear(reader);
	Py_DECREF(reader->handler);
	PyObject_Del(self);
}

static MarkupType parse_markup(PreparsingReaderObject *reader,size_t *len){
LexicalState new_state;
MarkupType current_markup;
char c;

	current_markup=MT_NONE_YET;
	while(reader->buffer_pos<reader->buffer_end && current_markup==MT_NONE_YET) {
		c=reader->buffer[reader->buffer_pos++];
#ifdef STREAM_DEBUG
		putc(c,stdout);
#endif
		new_state=reader->lex_state;
		switch(reader->lex_state) {
		case LS_OUTER:
			if (c=='<') {
				new_state=LS_TSTART;
				if (reader->buffer_pos>1) {
					current_markup=MT_CDATA;
					*len=reader->buffer_pos-1;
				}
			}
			break;
		case LS_TSTART:
			switch(c){
			case '/':
				new_state=LS_ETCONT;
				break;
			case '?':
				new_state=LS_PI;
				break;
			case '!':
				new_state=LS_DSTART;
				break;
			case '>':
				new_state=LS_OUTER;
				current_markup=MT_ERROR;
				*len=reader->buffer_pos;
				break;
			default:
				new_state=LS_TCONT;
				break;
			}
			break;
		case LS_TCONT:
			switch(c){
			case '/':
				new_state=LS_TSLASH;
				break;
			case '>':
				new_state=LS_OUTER;
				current_markup=MT_START_TAG;
				*len=reader->buffer_pos;
				break;
			case '"':
			case '\'':
				new_state=LS_TQVAL;
				reader->lex_quote=c;
				break;
			default:
				break;
			}
			break;
		case LS_TSLASH:
			switch(c){
			case '>':
				new_state=LS_OUTER;
				current_markup=MT_EMPTY_ELEMENT;
				*len=reader->buffer_pos;
				break;
			default:
				new_state=LS_OUTER;
				current_markup=MT_ERROR;
				*len=reader->buffer_pos;
				break;
			}
			break;
		case LS_TQVAL:
			if (c==reader->lex_quote)
				new_state=LS_TCONT;
			else if (c=='<')
				new_state=LS_TCDATASTART1;
			break;
		case LS_TCDATASTART1:
			switch(c){
			case '!':
				new_state=LS_TCDATASTART2;
				break;
			default:
				new_state=LS_TQVAL;
				current_markup=MT_ERROR;
				*len=reader->buffer_pos;
				break;
			}
			break;
		case LS_TCDATASTART2:
			switch(c){
			case '[':
				new_state=LS_TCDATASTART3;
				break;
			default:
				new_state=LS_TQVAL;
				current_markup=MT_ERROR;
				*len=reader->buffer_pos;
				break;
			}
			break;
		case LS_TCDATASTART3:
			switch(c){
			case 'C':
				new_state=LS_TCDATASTART4;
				break;
			default:
				new_state=LS_TQVAL;
				current_markup=MT_ERROR;
				*len=reader->buffer_pos;
				break;
			}
			break;
		case LS_TCDATASTART4:
			switch(c){
			case 'D':
				new_state=LS_TCDATASTART5;
				break;
			default:
				new_state=LS_TQVAL;
				current_markup=MT_ERROR;
				*len=reader->buffer_pos;
				break;
			}
			break;
		case LS_TCDATASTART5:
			switch(c){
			case 'A':
				new_state=LS_TCDATASTART6;
				break;
			default:
				new_state=LS_TQVAL;
				current_markup=MT_ERROR;
				*len=reader->buffer_pos;
				break;
			}
			break;
		case LS_TCDATASTART6:
			switch(c){
			case 'T':
				new_state=LS_TCDATASTART7;
				break;
			default:
				new_state=LS_TQVAL;
				current_markup=MT_ERROR;
				*len=reader->buffer_pos;
				break;
			}
			break;
		case LS_TCDATASTART7:
			switch(c){
			case 'A':
				new_state=LS_TCDATASTART8;
				break;
			default:
				new_state=LS_TQVAL;
				current_markup=MT_ERROR;
				*len=reader->buffer_pos;
				break;
			}
			break;
		case LS_TCDATASTART8:
			switch(c){
			case '[':
				new_state=LS_TCDATA;
				break;
			default:
				new_state=LS_TQVAL;
				current_markup=MT_ERROR;
				*len=reader->buffer_pos;
				break;
			}
			break;
		case LS_TCDATA:
			switch(c){
			case ']':
				new_state=LS_TCDATAEND1;
				break;
			default:
				break;
			}
			break;
		case LS_TCDATAEND1:
			switch(c){
			case ']':
				new_state=LS_TCDATAEND2;
				break;
			default:
				new_state=LS_TCDATA;
				break;
			}
			break;
		case LS_TCDATAEND2:
			switch(c){
			case '!':
				new_state=LS_TCDATAEND3;
				break;
			default:
				new_state=LS_TCDATA;
				break;
			}
			break;
		case LS_TCDATAEND3:
			switch(c){
			case '>':
				new_state=LS_TQVAL;
				break;
			default:
				new_state=LS_TCDATA;
				break;
			}
			break;
		case LS_ETCONT:
			switch(c){
			case '>':
				new_state=LS_OUTER;
				current_markup=MT_END_TAG;
				*len=reader->buffer_pos;
				break;
			default:
				break;
			}
			break;
		case LS_PI:
			switch(c){
			case '?':
				new_state=LS_PIEND;
				break;
			default:
				break;
			}
			break;
		case LS_PIEND:
			switch(c){
			case '>':
				new_state=LS_OUTER;
				current_markup=MT_IGNORE;
				*len=reader->buffer_pos;
				break;
			default:
				new_state=LS_PI;
				break;
			}
			break;
		case LS_DSTART:
			switch(c){
			case '-':
				new_state=LS_CSTART;
				break;
			case '[':
				new_state=LS_CDATASTART3;
				break;
			default:
				new_state=LS_OUTER;
				current_markup=MT_ERROR;
				*len=reader->buffer_pos;
				break;
			}
			break;
		case LS_CSTART:
			switch(c){
			case '-':
				new_state=LS_COMMENT;
				break;
			default:
				new_state=LS_OUTER;
				current_markup=MT_ERROR;
				*len=reader->buffer_pos;
				break;
			}
			break;
		case LS_COMMENT:
			switch(c){
			case '-':
				new_state=LS_COMMENTEND1;
				break;
			default:
				break;
			}
			break;
		case LS_COMMENTEND1:
			switch(c){
			case '-':
				new_state=LS_COMMENTEND2;
				break;
			default:
				new_state=LS_COMMENT;
				break;
			}
			break;
		case LS_COMMENTEND2:
			switch(c){
			case '>':
				new_state=LS_OUTER;
				current_markup=MT_IGNORE;
				*len=reader->buffer_pos;
				break;
			default:
				new_state=LS_COMMENT;
				current_markup=MT_ERROR;
				*len=reader->buffer_pos;
				break;
			}
			break;
		case LS_CDATASTART3:
			switch(c){
			case 'C':
				new_state=LS_CDATASTART4;
				break;
			default:
				new_state=LS_OUTER;
				current_markup=MT_ERROR;
				*len=reader->buffer_pos;
				break;
			}
			break;
		case LS_CDATASTART4:
			switch(c){
			case 'D':
				new_state=LS_CDATASTART5;
				break;
			default:
				new_state=LS_OUTER;
				current_markup=MT_ERROR;
				*len=reader->buffer_pos;
				break;
			}
			break;
		case LS_CDATASTART5:
			switch(c){
			case 'A':
				new_state=LS_CDATASTART6;
				break;
			default:
				new_state=LS_OUTER;
				current_markup=MT_ERROR;
				*len=reader->buffer_pos;
				break;
			}
			break;
		case LS_CDATASTART6:
			switch(c){
			case 'T':
				new_state=LS_CDATASTART7;
				break;
			default:
				new_state=LS_OUTER;
				current_markup=MT_ERROR;
				*len=reader->buffer_pos;
				break;
			}
			break;
		case LS_CDATASTART7:
			switch(c){
			case 'A':
				new_state=LS_CDATASTART8;
				break;
			default:
				new_state=LS_OUTER;
				current_markup=MT_ERROR;
				*len=reader->buffer_pos;
				break;
			}
			break;
		case LS_CDATASTART8:
			switch(c){
			case '[':
				new_state=LS_CDATA;
				break;
			default:
				new_state=LS_OUTER;
				current_markup=MT_ERROR;
				*len=reader->buffer_pos;
				break;
			}
			break;
		case LS_CDATA:
			switch(c){
			case ']':
				new_state=LS_CDATAEND1;
				break;
			default:
				break;
			}
			break;
		case LS_CDATAEND1:
			switch(c){
			case ']':
				new_state=LS_CDATAEND2;
				break;
			default:
				new_state=LS_CDATA;
				break;
			}
			break;
		case LS_CDATAEND2:
			switch(c){
			case '!':
				new_state=LS_CDATAEND3;
				break;
			default:
				new_state=LS_CDATA;
				break;
			}
			break;
		case LS_CDATAEND3:
			switch(c){
			case '>':
				new_state=LS_OUTER;
				break;
			default:
				new_state=LS_CDATA;
				break;
			}
			break;
		}
#ifdef STREAM_DEBUG
		if (new_state!=reader->lex_state) {
			printf("(new state: %i)",(int)new_state);
		}
#endif
		reader->lex_state=new_state;
	}
	return current_markup;
}

static xmlDocPtr parse_fragment(PreparsingReaderObject *reader,const char *f,size_t flen){
char *buf;
char c;
int i;
xmlDocPtr doc;

	buf=PyMem_New(char,reader->document_start_len*2+flen+1);
	if (buf==NULL) return NULL;
	memcpy(buf,reader->document_start,reader->document_start_len);
	memcpy(buf+reader->document_start_len,f,flen);
	buf[reader->document_start_len+flen]='<';
	buf[reader->document_start_len+flen+1]='/';
	for(i=1;i<reader->document_start_len;i++){
		c=reader->document_start[i];
		if (c==' ' || c=='\t' || c=='\n' || c=='\r' || c=='>') break;
		buf[reader->document_start_len+flen+i+1]=c;
	}
	buf[reader->document_start_len+flen+i+1]='>';
	doc=xmlParseMemory(buf,reader->document_start_len+flen+i+2);
	PyMem_Del(buf);
	return doc;
}

static int stream_start(PreparsingReaderObject *reader,MarkupType mtype,int len){
PyObject *obj;
	
	if (reader->doc) xmlFreeDoc(reader->doc);
	PyMem_Del(reader->document_start);
	if (mtype==MT_START_TAG){
		reader->document_start=PyMem_New(char,len);
		if (reader->document_start) {
			memcpy(reader->document_start,reader->buffer,len);
			reader->document_start_len=len;
			reader->doc=parse_fragment(reader,"",0);
		}
		else reader->doc=NULL;
	}
	else {
		reader->document_start=NULL;
		reader->doc=xmlParseMemory(reader->buffer,len);
	}
	if (reader->doc==NULL) {
		preparsing_reader_clear(reader);
		PyErr_SetString(MyError,"XML not well-formed.");
		return -1;
	}
	obj=PyObject_CallMethod(reader->handler,"_stream_start","O",
			libxml_xmlDocPtrWrap(reader->doc));
	if (obj==NULL) reader->exception=1;
	else Py_DECREF(obj);
	if (mtype==MT_EMPTY_ELEMENT){
		obj=PyObject_CallMethod(reader->handler,"_stream_end","O",
				libxml_xmlDocPtrWrap(reader->doc));
		if (obj==NULL) reader->exception=1;
		else Py_DECREF(obj);
		reader->eof=1;
	}
	reader->current_stanza_end=0;
	return 0;
}

static int stream_end(PreparsingReaderObject *reader,int len){
PyObject *obj;
char *buf;
	
	if (reader->doc) xmlFreeDoc(reader->doc);
	reader->doc=NULL;
	buf=PyMem_New(char,len+reader->document_start_len);
	if (buf==NULL) {
		PyErr_Format(MyError,"Out of memory? Couldn't allocate %d bytes in stream_end()",(int)(len+reader->document_start_len));
		return -1;
	}
	memcpy(buf,reader->document_start,reader->document_start_len);
	memcpy(buf+reader->document_start_len,reader->buffer,len);
	reader->doc=xmlParseMemory(buf,len+reader->document_start_len);
	if (reader->doc==NULL) {
		preparsing_reader_clear(reader);
		PyErr_SetString(MyError,"XML not well-formed.");
		return -1;
	}
	obj=PyObject_CallMethod(reader->handler,"_stream_end","O",
			libxml_xmlDocPtrWrap(reader->doc));
	if (obj==NULL) reader->exception=1;
	else Py_DECREF(obj);
	reader->eof=1;
	return 0;
}


static int append_to_current_stanza(PreparsingReaderObject *reader,int len){

	if (reader->current_stanza_end+len>reader->current_stanza_len) {
		reader->current_stanza_len+=(len/1024+1)*1024;
		reader->current_stanza=PyMem_Resize(reader->current_stanza,char,
				reader->current_stanza_len);
		if (reader->current_stanza==NULL) {
			preparsing_reader_clear(reader);
			PyErr_Format(MyError,"Out of memory? Couldn't allocate %d bytes in append_to_current_stanza()",(int)reader->current_stanza_len);
			return -1;
		}
	}
	memcpy(reader->current_stanza+reader->current_stanza_end,reader->buffer,len);
	reader->current_stanza_end+=len;
	return 0;
}

static int process_stanza(PreparsingReaderObject *reader){
PyObject *obj;
xmlDocPtr doc;
xmlNodePtr node;
xmlNodePtr stanza;

	doc=parse_fragment(reader,reader->current_stanza,reader->current_stanza_end);
	if (doc==NULL) {
		preparsing_reader_clear(reader);
		PyErr_SetString(MyError,"XML not well-formed.");
		return -1;
	}
	
	node=xmlDocGetRootElement(doc);
	node=node->children;
	while(node!=NULL && node->type!=XML_ELEMENT_NODE) node=node->next;

	if (node==NULL) {
		preparsing_reader_clear(reader);
		PyErr_SetString(MyError,"Unexpected XML stream parsing error.");
		return -1;
	}

	stanza=xmlDocCopyNode(node,reader->doc,1);

	xmlAddChild(xmlDocGetRootElement(reader->doc),stanza);
	xmlFreeDoc(doc);
	
	obj=PyObject_CallMethod(reader->handler,"_stanza","OO",
			libxml_xmlDocPtrWrap(reader->doc),libxml_xmlNodePtrWrap(stanza));
	if (obj==NULL) reader->exception=1;
	else Py_DECREF(obj);

	xmlUnlinkNode(stanza);
	xmlFreeNode(stanza);
	
	reader->current_stanza_end=0;
	return 0;
}


static PyObject * preparsing_reader_feed(PyObject *self, PyObject *args) {
PreparsingReaderObject *reader=(PreparsingReaderObject *)self;
char *str;
size_t len;
int tmp_len;
MarkupType mtype;
int depth_change;
size_t i;

	if (reader->eof){
		Py_INCREF(Py_None);
		return Py_None;
	}

	if (!PyArg_ParseTuple(args, "s#", &str, &tmp_len)) return NULL;
	len=(size_t)tmp_len;
	reader->exception=0;
			
	if (reader->buffer_end+len>reader->buffer_len) {
		reader->buffer_len+=(len/1024+1)*1024;
		reader->buffer=PyMem_Resize(reader->buffer,char,reader->buffer_len);
		if (reader->buffer==NULL) {
			/* out of memory */
			preparsing_reader_clear(reader);
			PyErr_Format(MyError,"Out of memory? Couldn't allocate %d bytes in preparsing_reader_feed()",(int)reader->buffer_len);
			return NULL;
		}
	}
	memcpy(reader->buffer+reader->buffer_end,str,len);
	reader->buffer_end+=len;

	if (reader->buffer_pos==reader->buffer_end){
		reader->eof=1;
		Py_INCREF(Py_None);
		return Py_None;
	}

	while(reader->buffer_pos<reader->buffer_end){
		mtype=parse_markup(reader,&len);
		if (mtype==MT_ERROR) {
			preparsing_reader_clear(reader);
			PyErr_SetString(MyError,"XML not well-formed or unsupported XML feature.");
			return NULL;
		}
		if (mtype==MT_NONE_YET) continue;
#ifdef STREAM_DEBUG
		printf("{[%i]",reader->depth);
		if (mtype==MT_IGNORE){
			printf("ignoring: ");
		}
		else if (mtype==MT_START_TAG){
			printf("start tag: ");
		}
		else if (mtype==MT_END_TAG){
			printf("end tag: ");
		}
		else if (mtype==MT_EMPTY_ELEMENT){
			printf("empty element: ");
		}
		else if (mtype==MT_CDATA){
			printf("cdata: ");
		}
		printf("'");
		fwrite(reader->buffer,1,len,stdout);
		printf("'}");
#endif
		depth_change=0;
		if (reader->depth==0) {
			switch(mtype){
			case MT_START_TAG:
				depth_change=1;
			case MT_EMPTY_ELEMENT:
				if (stream_start(reader,mtype,len))
					return NULL;
				break;
			case MT_IGNORE:
				break;
			case MT_CDATA:
				for(i=0;i<len;i++){
					if (reader->buffer[i]!=' '
						&& reader->buffer[i]!='\t'
						&& reader->buffer[i]!='\r'
						&& reader->buffer[i]!='\n') break;
				}
				if (i==len) break;
			default:
				preparsing_reader_clear(reader);
				PyErr_SetString(MyError,"XML not well-formed "
						"or unsupported XML feature.");
				return NULL;
			}
		}
		else if (reader->depth==1) {
			switch(mtype){
			case MT_START_TAG:
				reader->current_stanza_end=0;
				if (append_to_current_stanza(reader,len))
					return NULL;
				depth_change=1;
				break;
			case MT_END_TAG:
				if (stream_end(reader,len))
					return NULL;
				depth_change=-1;
				break;
			case MT_EMPTY_ELEMENT:
				reader->current_stanza_end=0;
				if (append_to_current_stanza(reader,len))
					return NULL;
				if (process_stanza(reader))
					return NULL;
				break;
			case MT_IGNORE:
			case MT_CDATA:
				break;
			default:
				preparsing_reader_clear(reader);
				PyErr_SetString(MyError,"XML not well-formed "
						"or unsupported XML feature.");
				return NULL;
			}
		}
		else {
			switch(mtype){
			case MT_START_TAG:
			case MT_END_TAG:
			case MT_EMPTY_ELEMENT:
			case MT_CDATA:
				if (append_to_current_stanza(reader,len))
					return NULL;
				break;
			case MT_IGNORE:
				break;
			default:
				preparsing_reader_clear(reader);
				PyErr_SetString(MyError,"XML not well-formed "
						"or unsupported XML feature.");
				return NULL;
			}
			switch(mtype){
			case MT_START_TAG:
				depth_change=1;
				break;
			case MT_END_TAG:
				if (reader->depth==2 && process_stanza(reader))
					return NULL;
				depth_change=-1;
				break;
			default:
				break;
			}
		}
		reader->depth+=depth_change;
		memmove(reader->buffer,reader->buffer+len,reader->buffer_end-len);
		reader->buffer_end-=len;
		reader->buffer_pos-=len;
		if (reader->exception) return NULL;
	}
	
	return Py_BuildValue("i", reader->buffer_pos<reader->buffer_end);
}

static PyObject * preparsing_reader_doc(PyObject *self, PyObject *args) {
	Py_INCREF(Py_None);
	return Py_None;
}

static PyMethodDef preparsing_reader_methods[] = {
	{(char *)"feed", preparsing_reader_feed, METH_VARARGS, NULL},
	{(char *)"doc", preparsing_reader_doc, METH_VARARGS, NULL},
	{NULL, NULL, 0, NULL}
};

static PyObject * preparsing_reader_getattr(PyObject *obj, char *name) {
PreparsingReaderObject *reader=(PreparsingReaderObject *)obj;

	return Py_FindMethod(preparsing_reader_methods, (PyObject *)reader, name);
}
 
static int preparsing_reader_setattr(PyObject *obj, char *name, PyObject *v) {
	(void)PyErr_Format(PyExc_RuntimeError, "Read-only attribute: \%s", name);
	return -1;
}

static PyTypeObject PreparsingReaderType = {
	PyObject_HEAD_INIT(NULL)
	0,
	"_Reader",
	sizeof(PreparsingReaderObject),
	0,
	preparsing_reader_free, /*tp_dealloc*/
	0,          /*tp_print*/
	preparsing_reader_getattr, /*tp_getattr*/
	preparsing_reader_setattr, /*tp_setattr*/
	0,          /*tp_compare*/
	0,          /*tp_repr*/
	0,          /*tp_as_number*/
	0,          /*tp_as_sequence*/
	0,          /*tp_as_mapping*/
	0,          /*tp_hash */
};
#endif

static PyMethodDef xmlextraMethods[] = {
	{(char *)"replace_ns", replace_ns, METH_VARARGS, NULL },
	{(char *)"remove_ns", remove_ns, METH_VARARGS, NULL },
#if 1
	{(char *)"sax_reader_new", sax_reader_new, METH_VARARGS, NULL},
#else
	{(char *)"preparsing_reader_new", preparsing_reader_new, METH_VARARGS, NULL},
#endif
	{NULL, NULL, 0, NULL}
};

void init_xmlextra(void) {
static int initialized = 0;
PyObject *m, *d;

	if (initialized != 0) return;
#if 1
	SaxReaderType.ob_type = &PyType_Type;
#else
	PreparsingReaderType.ob_type = &PyType_Type;
#endif
	m = Py_InitModule((char *) "_xmlextra", xmlextraMethods);
	d = PyModule_GetDict(m);
	MyError = PyErr_NewException("_xmlextra.error", NULL, NULL);
	PyDict_SetItemString(d, "error", MyError);
	PyDict_SetItemString(d, "__revision__", PyString_FromString("$Id: xmlextra.c,v 1.6 2004/10/04 13:01:18 jajcus Exp $"));
	PyDict_SetItemString(d, "__docformat__", PyString_FromString("restructuredtext en"));
	PyDict_SetItemString(d, "__doc__", 
			PyString_FromString("Special libxml2 extensions for PyXMPP internal use."));
	initialized = 1;
}
