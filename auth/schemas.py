from marshmallow import Schema, fields

class LoginRequestSchema(Schema):
    email = fields.Email(required=True)
    password = fields.String(required=True)


class RegisterRequestSchema(Schema):
    nama = fields.String(required=True)
    email = fields.Email(required=True)
    password = fields.String(required=True)
    no_telepon = fields.String(required=True)


class AuthResponseSchema(Schema):
    message = fields.String()
    user = fields.Dict()
    token = fields.String()
