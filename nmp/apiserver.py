#!/usr/bin/env python

import json
import threading
from flask import Flask, request
from flask_restplus import Resource, Api, fields
from werkzeug.middleware.proxy_fix import ProxyFix

class NmpApi:
    def __init__(self, nmpserver=None):
        self.nmp = nmpserver
        self.namesapce = 'v1'

    def set_encoder_pool(self, pool):
        self.encoder_pool = pool

    def run(self, port):
        self.thread = threading.Thread(target=self.start_service, args=(port,))
        self.thread.daemon = True
        self.thread.start()

    def auth(self, uuid):
        return True

    def alloc_token(self, n):
        encoders = self.encoder_pool.dynamic_alloc(n)
        if not len(encoders):
            return False, 'fail to alloc'
        else:
            dumps_encoders = {}
            for k, v in encoders.items():
                dumps_encoders[k] = v.dumps()

            return True, json.dumps(dumps_encoders)

    def dealloc_token(self, tokens):
        self.encoder_pool.dealloc(tokens)
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
        alloc_args = self.api.parser()
        alloc_args.add_argument('uuid', required=True, help='uuid')
        alloc_args.add_argument('n', required=True, help='n encoders')

        dealloc_args = self.api.parser()
        dealloc_args.add_argument('uuid', required=True, help='uuid')
        dealloc_args.add_argument('tokens', required=True, help='tokens')

        # Api
        @namespace.route('/connect')
        @namespace.expect(alloc_args)
        class Connect(Resource):
            @namespace.marshal_with(status_model, envelope='data')
            def post(self):
                args = alloc_args.parse_args()
                if not apiserver.auth(args['uuid']):
                    return {'status': False, 'data': 'auth fail'}

                status, message = apiserver.alloc_token(int(args['n']))
                return {'status': status, 'data': message}

        @namespace.route('/disconnect')
        @namespace.expect(dealloc_args)
        class Disconnect(Resource):
            @namespace.marshal_with(status_model, envelope='data')
            def delete(self):
                args = dealloc_args.parse_args()
                if not apiserver.auth(args['uuid']):
                    return {'status': False, 'data': 'auth fail'}

                tokens = json.loads(args['tokens'])
                print(tokens)
                status, message = apiserver.dealloc_token(tokens)
                return {'status': status, 'data': message}

        self.app.run(host='0.0.0.0', port=port)


if '__main__' == __name__:
    apiserver = NmpApi()
    apiserver.run(port=2333)
