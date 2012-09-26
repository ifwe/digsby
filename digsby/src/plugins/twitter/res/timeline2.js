
function FeedView(container, objToNode, objId, nodeKey, itemKey)
{
    this.container = container;
    this.createDOMNode = objToNode;
    this.getObjId = objId;
    this.getVisualKey = nodeKey;
    this.getItemKey = itemKey;

    this.resetStats();
}

FeedView.prototype = {

    resetStats: function() {
        this.stats = {
            inserts: 0,
            deletes: 0
        };
    },
    
    /**
     * syncs this visual list with the model given in "items"
     */
    sync: function(items) {
        var self = this;

        // find spans to delete
        var node = this.container.firstChild;
        var index = 0;
        var deleteSpan = [];
        var toDelete;

        function getId(node) { return node.id; }

        var lastDeletedNode = undefined;

        var insertFragment, beforeNode;

        function deleteNode(node) {
            if (beforeNode === node)
                beforeNode = beforeNode.nextSibling;
            node.parentNode.removeChild(node);
            ++self.stats.deletes;
        }

        function insertNodes(items) {
            if (insertFragment === undefined) {
                insertFragment = document.createDocumentFragment();
                beforeNode = node;
            }

            for (var i = 0; i < items.length; ++i) {
                var newNode = self.createDOMNode(items[i]);
                assert(newNode);
                insertFragment.appendChild(newNode);
            }
        }

        function finish() {
            if (insertFragment !== undefined) {
                insertOrAppend(self.container, insertFragment, beforeNode);
                ++self.stats.inserts;
            }
            insertFragment = undefined;
        }

        while (index < items.length) {
            var item = items[index];

            if (!node) {
                // hit the end of the visual list--just add the rest
                insertNodes(items.slice(index));
                break;
            } 
            
            var val = getId(node).toString() === this.getObjId(item).toString();
            if (val) {
                // nodes are the same, advance both pointers
                feedSwitch(node);
                finish();
                node = node.nextSibling;
                ++index;
                continue;
            } else if (this.getVisualKey(node) < this.getItemKey(item)) {
                // the input list got ahead of us, delete a visual node
                finish();
                toDelete = node;
                node = node.nextSibling;
                deleteNode(toDelete);
                continue;
            } else {
                // insert a node
                insertNodes([item]);
                ++index;
            }
        }

        // delete any extra nodes that are left
        while (node) {
            toDelete = node;
            node = node.nextSibling;
            deleteNode(toDelete);
        }

        finish();
    }
}

function insertOrAppend(container, node, beforeNode) {
    assert(node);
    if (beforeNode)
        try {
            container.insertBefore(node, beforeNode);
        } catch (err) {
            console.warn('node: ' + node);
            console.warn('beforeNode: ' + beforeNode);
            console.warn('beforeNode.parentNode: ' + beforeNode.parentNode);
            console.warn(' -> ' + (beforeNode.parentNode === container));

            throw err;
        }
    else
        container.appendChild(node);
}

function feedSwitch(node) {
    guard(function() {
        // modify and tweets that are showing indented as "replies" 
        // to be back to normal
        var c = node.className.replace('reply', '');
        if (c === node.className)
            return;

        node.className = c;
        var replyTo = node.getElementsByClassName('in_reply_to');
        if (!(replyTo && replyTo.length))
            return;

        var as = replyTo[0].getElementsByTagName('a');
        if (as && as.length)
            as[0].style.display = 'inline';

    });
}

