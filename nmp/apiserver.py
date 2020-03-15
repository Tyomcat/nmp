#!/usr/bin/env python

import threading
from flask import Flask, request
from flask_restplus import Resource, Api, fields
from werkzeug.middleware.proxy_fix import ProxyFix

class NmpApi:
    def __init__(self, nmpserver=None):
        self.nmp = nmpserver
        self.namesapce = 'v1'

    def run(self, port):
        self.thread = threading.Thread(target=self.start_service, args=(port,))
        self.thread.daemon = True
        self.thread.start()

    def auth(self, uuid):
        return True

    def alloc_token(self):
        return True, 'token-xxx'

    def dealloc_token(self, token):
        return True, 'success'

    def start_service(self, port):
        apiserver = self
        self.app = Flask(__name__)
        self.app.wsgi_app = ProxyFix(self.app.wsgi_app)
        self.api = Api(self.app, version='1.0', title='NmpApi',
                       description='The Nmp Server Api')

        # Response model
        namespace = self.api.namespace(self.namesapce, description='nmp api')
        status_model = self.api.model(
            'Status', {
                'status': fields.Boolean,
                'data': fields.String
            })

        # Request arguments
        uuid_args = self.api.parser()
        uuid_args.add_argument('uuid', required=True, help='uuid')

        token_args = self.api.parser()
        token_args.add_argument('uuid', required=True, help='uuid')
        token_args.add_argument('token', required=True, help='token')

        # Api
        @namespace.route('/connect')
        @namespace.expect(uuid_args)
        class Connect(Resource):
            @namespace.marshal_with(status_model, envelope='data')
            def post(self):
                args = uuid_args.parse_args()
                if not apiserver.auth(args['uuid']):
                    return {'status': False, 'data': 'auth fail'}

                status, message = apiserver.alloc_token()
                return {'status': status, 'data': message}

        @namespace.route('/disconnect')
        @namespace.expect(token_args)
        class Disconnect(Resource):
            @namespace.marshal_with(status_model, envelope='data')
            def delete(self):
                args = token_args.parse_args()
                if not apiserver.auth(args['uuid']):
                    return {'status': False, 'data': 'auth fail'}

                status, message = apiserver.dealloc_token(args['token'])
                return {'status': status, 'data': message}

        self.app.run(host='0.0.0.0', port=port)


if '__main__' == __name__:
    apiserver = NmpApi()
    apiserver.run(port=2333)
