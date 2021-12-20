import logging

from datetime import datetime, timedelta

from flask import abort, jsonify
from webargs.flaskparser import use_args

from marshmallow import Schema, fields, ValidationError, validates_schema

from service.api.persons import PersonResultSchema
from service.server import app, db
from service.models import AddressSegment
from service.models import Person


class GetAddressQueryArgsSchema(Schema):
    date = fields.Date(required=False, missing=datetime.utcnow().date())


class AddressSchema(Schema):
    class Meta:
        ordered = True

    street_one = fields.Str(required=True, max=128)
    street_two = fields.Str(max=128)
    city = fields.Str(required=True, max=128)
    state = fields.Str(required=True, max=2)
    zip_code = fields.Str(required=True, max=10)

    start_date = fields.Date(required=True)
    end_date = fields.Date(required=False)
    # person_id = fields.Nested(PersonResultSchema(only=("id",)))

    # @validates_schema()
    # def validate_start_date(self, data, **kwargs):
    #     if type(data) == list:
    #         if data[0].get("person_id") is not None:
    #             most_recent_start_date = data[0].get("person_id")
    #             # query if works here
    #             if data <= most_recent_start_date:
    #                 raise ValidationError("Invalid start date")
    #         else:
    #             pass


@app.route("/api/persons/<uuid:person_id>/address", methods=["GET"])
@use_args(GetAddressQueryArgsSchema(), location="querystring")
def get_address(args, person_id):
    person = Person.query.get(person_id)
    if person is None:
        abort(404, description="person does not exist")
    elif len(person.address_segments) == 0:
        abort(404, description="person does not have an address, please create one")

    address_segment = person.address_segments[-1]
    return jsonify(AddressSchema().dump(address_segment))


@app.route("/api/persons/<uuid:person_id>/address", methods=["PUT"])
@use_args(AddressSchema())
def create_address(payload, person_id):

    person = Person.query.get(person_id)
    address_segment = AddressSegment(
        street_one=payload.get("street_one"),
        street_two=payload.get("street_two"),
        city=payload.get("city"),
        state=payload.get("state"),
        zip_code=payload.get("zip_code"),
        start_date=payload.get("start_date"),
        person_id=person_id,
    )
    if person is None:
        abort(404, description="person does not exist")
    # If there are no AddressSegment records present for the person, we can go
    # ahead and create with no additional logic.
    elif len(person.address_segments) == 0:
        db.session.add(address_segment)
        db.session.commit()
        db.session.refresh(address_segment)
    else:
        # TODO: Implementation
        # If there are one or more existing AddressSegments, create a new AddressSegment
        # that begins on the start_date provided in the API request and continues
        # into the future. If the start_date provided is not greater than most recent
        # address segment start_date, raise an Exception.

        most_recent_address = person.address_segments[-1]
        if address_segment.start_date <= most_recent_address.start_date:
            raise ValueError("Start date must be after current start date")
            # use below with try/except?
            #try:
               # AddressSchema().load([address_segment, most_recent_address], many=True)
            #except ValidationError as err:
                #err.message = "Start date must be after current start date"
        else:
            most_recent_address.end_date = address_segment.start_date
            db.session.add_all([most_recent_address, address_segment])
            db.session.commit()
            db.session.refresh(most_recent_address)
            db.session.refresh(address_segment)
    # make sure this doesnt happen if abort
    return jsonify(AddressSchema().dump(address_segment))
