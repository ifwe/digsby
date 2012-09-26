
// tiny HTML5 ORM

function SQLDesc(tableName, columns)
{
    this.tableName = tableName;
    this.columns = columns;
    this.allowedAttrs = makeAttrsSet(columns);

    this.insertPlaceholders = '(';

    var i;
    for (i = 0; i < columns.length - 1; ++i)
        this.insertPlaceholders += '?, ';
    this.insertPlaceholders += '?)';

    this.typeCoercions = {};
    for (i = 0; i < columns.length; ++i) {
        var type = columns[i][1];
        if (type.toLowerCase() === 'boolean') {
            columns[i][1] = 'integer';
            this.typeCoercions[columns[i][0]] = Number;
        }
    }
}


SQLDesc.prototype = {
    toString: function() {
        return '[SQLDesc ' + this.tableName + ']';
    },

    insertTransform: function(columnName, obj) {
        return columnName in this.typeCoercions ?
            new this.typeCoercions[columnName](obj) :
            obj;
    },

    createTableStatement: function () {
        var types = [];
        $.each(this.columns, function (i, column) {
            var name = column[0], type = column[1];
            types.push([name, type].join(' '));
        });
        var typesString = types.join(', ');

        return "CREATE TABLE IF NOT EXISTS " + this.tableName + " (" + typesString + ")";
    },

    ensureTableExists: function (tx, successCb, errorCb) {
        tx.executeSql(this.createTableStatement(), [], function(tx, result) {
            if (successCb)
                successCb(tx, result);
        }, function (tx, error) {
            if (errorCb)
                errorCb(tx, error);
        });
    },

    fromJSON: function (json, override) {
        var allowed = this.allowedAttrs;
        var obj = {};

        for (var key in json) {
            var value = (override ? override[key] : undefined) || json[key];
            if (allowed[key])
                obj[key] = value;
        }

        return obj;
    },

    insertOrReplace: function (tx, obj) {
        var vals = [];

        var cols = this.columns;
        for (var i = 0; i < cols.length; ++i) {
            var columnName = cols[i][0];
            var val = this.insertTransform(columnName, obj[columnName]);
            vals.push(val === undefined ? null : val);
        }

        var statement = 'INSERT OR REPLACE INTO ' + this.tableName + ' VALUES ' + this.insertPlaceholders;
        tx.executeSql(statement, vals);
    }
};

/**
 * makes a {columnName: true} hash set for a list of column names and types
 */
function makeAttrsSet(columns) {
    var attrsSet = {};
    for (var i = 0; i < columns.length; ++i)
        attrsSet[columns[i][0]] = true;
    return attrsSet;
}


