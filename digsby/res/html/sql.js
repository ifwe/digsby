
// tiny HTML5 ORM

function SQLDesc(tableName, columns)
{
    this.tableName = tableName;
    this.columns = columns;
    this.columns.push([this.extraColumnName, 'TEXT']);
    this.allowedAttrs = makeAttrsSet(columns);


    this.insertPlaceholders = '(';
    for (var i = 0; i < this.columns.length - 1; ++i)
        this.insertPlaceholders += '?, ';
    this.insertPlaceholders += '?)';
}

SQLDesc.prototype = {
    insertTransform: function(columnName, obj) { return obj; },
    extraColumnName: 'extra_attributes',

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
        var extra = {};
        var obj = {};

        for (var key in json) {
            var value = (override ? override[key] : undefined) || json[key];
            if (allowed[key])
                obj[key] = value;
            else
                extra[key] = value;
        }

        if (extra.length)
            obj[this.extraColumnName] = extra;

        return obj;
    },

    insertOrReplace: function (tx, obj) {
        var vals = [];

        var cols = this.columns;
        for (var i = 0; i < cols.length - 1; ++i) {
            var columnName = cols[i][0];
            var val = this.insertTransform(columnName, obj[columnName]);
            vals.push(val === undefined ? null : val);
        }

        var extra = {};
        if (0) {
            for (var key in obj) {
                if (!this.allowedAttrs[key])
                    extra[key] = obj[key];
            }
        }
    
        vals.push(extra.length ? JSON.stringify(extra) : null);

        var statement = 'INSERT OR REPLACE INTO ' + this.tableName + ' VALUES ' + this.insertPlaceholders;
        // console.log(statement);
        // console.log(vals);
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


