#!/usr/bin/env python
# -*- coding: utf-8 -*-

import datetime
import enum
import logging
import hashlib
from argparse import ArgumentParser
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import List, Annotated, Union, Optional
from pydantic import BaseModel, Field, model_validator

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


PhoneFieldStr = Annotated[str, Field(max_length=11, min_length=11, pattern=r'^7.*')]
PhoneFieldInt = Annotated[int, Field(le=79999999999, ge=70000000000)]
EmailField = Annotated[str, Field(pattern=r'.@.')]
StrField = Annotated[str, Field()]
DateField = Annotated[str, Field(pattern=r'\d\d\.\d\d.\d\d\d\d')]
ClientIDsField = Annotated[List[int], Field()]


class GenderEnum(enum.Enum):
    UNKNOWN = 0
    MALE = 1
    FEMALE = 2


class ClientsInterestsRequest(BaseModel):
    client_ids: Optional[ClientIDsField] = None
    date: Optional[DateField] = None


class OnlineScoreRequest(BaseModel):
    first_name: Optional[StrField] = None
    last_name: Optional[StrField] = None
    email: Optional[EmailField] = None
    phone: Optional[Union[PhoneFieldInt, PhoneFieldStr]] = None
    birthday: Optional[DateField] = None
    gender: Optional[GenderEnum] = None

    @model_validator(mode='after')
    def check_data(self):
        first_name = self.first_name
        last_name = self.last_name

        email = self.email
        phone = self.phone

        birthday = self.birthday
        gender = self.gender

        if (first_name is None or last_name is None)\
                and (email is None or phone is None)\
                and (birthday is None or gender is None):
            return None
        return self


class MethodRequest(BaseModel):
    account: Optional[StrField] = None
    login: StrField = ''
    method: StrField = ''
    token: StrField = ''
    arguments: Union[OnlineScoreRequest, ClientsInterestsRequest] = None

    @property
    def is_admin(self):
        return self.login == ADMIN_LOGIN


class MainHandler(BaseHTTPRequestHandler):
    @staticmethod
    def get_result(request, context, settings):
        # Проверка на наличие необходимых полей в запросе
        request: MethodRequest = MethodRequest(**request.get('body'))

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
        arguments = request.arguments
        if type(arguments) != OnlineScoreRequest:
            return {'Пропущены все поля'}, INVALID_REQUEST
        if request.login == ADMIN_LOGIN:
            score = int(ADMIN_SALT)
            return {"score": score}, OK
        score = scoring.get_score(arguments)
        has = []
        for key, value in arguments.__dict__.items():
            if value:
                has.append(key)
        context["has"] = has
        return {"score": score}, OK

    @staticmethod
    def handle_clients_interests(request, context):
        arguments = request.arguments
        if not arguments:
            return {'Пропущены все поля'}, INVALID_REQUEST
        client_ids = arguments.client_ids
        if not client_ids:
            return {'Пропущено поле client_ids'}, INVALID_REQUEST
        interests = {client_id: scoring.get_interests() for client_id in client_ids}
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
