# -*- coding: utf-8 -*-

from flask import Flask, jsonify
from flask_sqlalchemy import SQLAlchemy
from marshmallow_sqlalchemy import ModelSchema

app = Flask(__name__, static_folder=None)
app.config['DEBUG'] = True
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///sample.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

class Bank(db.Model):
    __tablename__ = 'bank'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.Unicode, unique=True, nullable=False)
    bcra_code = db.Column(db.Unicode(8))
    cuit = db.Column(db.Unicode(11))

    def __repr__(self):
        return "<Bank '{}'>".format(self.name)


class BankSchema(ModelSchema):

    class Meta:
        model = Bank

@app.route('/banks')
def list_banks():
    q = Bank.query.all()
    return jsonify(
        {'data': BankSchema(many=True).dump(q).data}
    ), 200, {'X-Total-Count': len(q)}


# Desired Api
#import pudb; pudb.set_trace()
from tonic import Api, Resource, ModelResource, Route

class BankResource(ModelResource):

    class Meta:
        model = Bank
        #name = 'bank'


class SearchResource(Resource):

    class Meta:
        name = 'search'

    @Route.POST('', rel='result')
    def result(self):
        return "search result"


api = Api(app, prefix='/api')
api.register_resource(BankResource)
api.register_resource(SearchResource)
# End desired Api


# only for debug purpose
@app.route('/urls')
def show_urls():
    column_headers = ('Rule', 'Endpoint', 'Methods')
    order = 'rule'
    rows = [('-'*4, '-'*8, '-'*9)]  # minimal values to take
    rules = sorted(app.url_map.iter_rules(),
                key=lambda rule: getattr(rule, order))
    for rule in rules:
        rows.append((rule.rule, rule.endpoint, ', '.join(rule.methods)))

    rule_l = len(max(rows, key=lambda r: len(r[0]))[0])
    ep_l = len(max(rows, key=lambda r: len(r[1]))[1])
    meth_l = len(max(rows, key=lambda r: len(r[2]))[2])

    str_template = '%-' + str(rule_l) + 's' + \
                ' %-' + str(ep_l) + 's' + \
                ' %-' + str(meth_l) + 's'
    table_width = rule_l + 2 + ep_l + 2 + meth_l

    out = (str_template % column_headers) + '\n' + '-' * table_width
    for row in rows[1:]:
        out += '\n' + str_template % row

    return out+'\n', 200, {'Content-Type': 'text/table'}


if __name__ == "__main__":
    db.create_all()
    app.run()
