'''
Created on Nov 23, 2010

@author: Christopher Stelma

A topological sort based on finishing time,
which does not have a problem with cycles.
'''
from structures import oset
from util.primitives.mapping import odict, dictreverse
from collections import defaultdict

def add_node(graph, incidence, node):
    """Add a node to the graph if not already exists."""
    graph.setdefault(node, oset())
    incidence.setdefault(node, 0)

def add_arc(graph, incidence, u, v):
    graph[u].add(v)
    incidence[v] = incidence.get(v, 0) + 1

def create_graph(chains, incidence):
    graph = odict()
    for chain in chains:
        if not len(chain):
            continue
        add_node(graph, incidence, chain[0])
#        for i in range(len(chain)-1):
#            add_node(graph, incidence, chain[i+1])
#            add_arc(graph, incidence, chain[i], chain[i+1])
        for i in range(len(chain)):
            add_node(graph, incidence, chain[i])
            for j in range(i, len(chain)):
                add_arc(graph, incidence, chain[i], chain[j])
    return graph

WHITE = 'WHITE'
BLACK = 'BLACK'
GREY  = 'GREY'

def DFS(G, color, pred, disc, fin):
    for u in G:
        color[u] = WHITE
        pred[u]  = None
    time = 0
    for u in G:
        if color[u] == WHITE:
            time = DFSvisit(u, G, color, pred, disc, fin, time)

def DFSvisit(u, G, color, pred, disc, fin, time):
    color[u] = GREY
    time = time+1
    disc[u] = time
    for v in G[u]:
        if color[v] == WHITE:
            pred[v] = u
            time = DFSvisit(v, G, color, pred, disc, fin, time)
    color[u] = BLACK
    time = time+1
    fin[u] = time
    return time

def topological_sort_chains(chains):
    incidence = dict()
    G = create_graph(chains, incidence)
    assert len(G) == len(incidence)
    color = {}
    pred = {}
    disc = {}
    fin = {}
    DFS(G, color, pred, disc, fin)
    fin2 = dictreverse(fin)
    fin3 = []
    for i in sorted(fin2, reverse=True):
        fin3.append(fin2[i])
    return fin3

if __name__ == '__main__':
    incidence = dict()
    G = create_graph([ [6, 0, 5], [5, 6, 9, 3, 8, 7, 4, 2], [1, 0], [5, 6, 1, 0, 9, 3, 8, 7, 4, 2]], incidence)
    assert len(G) == len(incidence)
    color = {}
    pred = {}
    disc = {}
    fin = {}
    DFS(G, color, pred, disc, fin)
    from mapping import dictreverse
    fin2 = dictreverse(fin)
    fin3 = []
    for i in sorted(fin2, reverse=True):
        fin3.append(fin2[i])
    print fin3
#    print incidence

