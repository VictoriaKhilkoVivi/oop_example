#!/usr/bin/env python
# -*- coding: utf-8 -*-

import abc
import json
import datetime
import logging
import hashlib
import uuid
from argparse import ArgumentParser
from dataclasses import dataclass, Field
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import List

import scoring


SALT = "Otus"
ADMIN_LOGIN = "admin"
ADMIN_SALT = "42"
OK = 200
BAD_REQUEST = 400
FORBIDDEN = 403
NOT_FOUND = 404
INVALID_REQUEST = 422
INTERNAL_ERROR = 500
ERRORS = {
    BAD_REQUEST: "Bad Request",
    FORBIDDEN: "Forbidden",
    NOT_FOUND: "Not Found",
    INVALID_REQUEST: "Invalid Request",
    INTERNAL_ERROR: "Internal Server Error",
}
UNKNOWN = 0
MALE = 1
FEMALE = 2
GENDERS = {
    UNKNOWN: "unknown",
    MALE: "male",
    FEMALE: "female",
}


@dataclass
class CharField(str):
    pass


@dataclass
class EmailField(CharField):
    pass


@dataclass
class PhoneField(CharField):
    pass


@dataclass
class DateField(Field):
    pass


@dataclass
class BirthDayField(Field):
    pass


@dataclass
class GenderField(Field):
    pass


@dataclass
class ClientIDsField(List):
    type = List[int]


@dataclass
class ClientsInterestsRequest:
    client_ids: ClientIDsField
    date: DateField = None


@dataclass
class OnlineScoreRequest:
    first_name: CharField = None
    last_name: CharField = None
    email: EmailField = None
    phone: PhoneField = None
    birthday: BirthDayField = None
    gender: GenderField = None


@dataclass
class ArgumentsField(Field):
    pass


@dataclass
class MethodRequest:
    login: CharField
    token: CharField
    arguments: ArgumentsField
    method: CharField
    account: CharField = None

    @property
    def is_admin(self):
        return self.login == ADMIN_LOGIN


class MainHandler(BaseHTTPRequestHandler):
    @staticmethod
    def get_result(request, context, settings):
        # Проверка на наличие необходимых полей в запросе
        try:
            request: MethodRequest = MethodRequest(**request.get('body'))
        except TypeError as e:
            # if not request.get('account') or not request.get('login') or not request.method:
            return {'Пропущены поля'}, INVALID_REQUEST

        # Аутентификация
        if not MainHandler.is_valid_auth(request):
            return {}, FORBIDDEN

        # Обработка методов
        if request.method == "online_score":
            return MainHandler.handle_online_score(request, context)
        elif request.method == "clients_interests":
            return MainHandler.handle_clients_interests(request, context)

        return {'Ошибка обработки методов'}, INVALID_REQUEST

    @staticmethod
    def is_valid_auth(request: MethodRequest):
        if request.login == ADMIN_LOGIN:
            expected_token = hashlib.sha512(
                (datetime.datetime.now().strftime("%Y%m%d%H") + ADMIN_SALT).encode('utf-8')
            ).hexdigest()
            return request.token == expected_token
        else:
            msg = f'{request.account}{request.login}{SALT}'.encode('utf-8')
            expected_token = hashlib.sha512(msg).hexdigest()
            return request.token == expected_token

    @staticmethod
    def handle_online_score(request, context):
        try:
            OnlineScoreRequest(**request.arguments)
        except TypeError as e:
            return {'Пропущены поля'}, INVALID_REQUEST

        arguments = request.arguments
        # Здесь должна быть логика для расчета "online_score"
        if request.login == ADMIN_LOGIN:
            score = int(ADMIN_SALT)
            return {"score": score}, OK
        print(arguments)
        score = scoring.get_score(**arguments)
        context["has"] = arguments.keys()
        return {"score": score}, OK

    @staticmethod
    def handle_clients_interests(request, context):
        try:
            args = ClientsInterestsRequest(**request.arguments)
            if type(args.client_ids) != list[int]:
                return {'Пропущены поля'}, INVALID_REQUEST
        except TypeError as e:
            return {'Пропущены поля'}, INVALID_REQUEST

        arguments = request.arguments
        client_ids = arguments.get("client_ids")
        if not client_ids:
            return {'Пропущено поле client_ids'}, INVALID_REQUEST

        # client_ids = arguments.get("client_ids", [])
        # Здесь должна быть логика для получения интересов клиентов
        interests = {client_id: scoring.get_interests() for client_id in client_ids}
        # interests = scoring.get_interests(**arguments)
        context["nclients"] = len(client_ids)
        return interests, OK


if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument("-p", "--port", action="store", type=int, default=8080)
    parser.add_argument("-l", "--log", action="store", default=None)
    args = parser.parse_args()
    logging.basicConfig(filename=args.log, level=logging.INFO,
                        format='[%(asctime)s] %(levelname).1s %(message)s', datefmt='%Y.%m.%d %H:%M:%S')
    server = HTTPServer(("localhost", args.port), MainHandler)
    logging.info("Starting server at %s" % args.port)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    server.server_close()
