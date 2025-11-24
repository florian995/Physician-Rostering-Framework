import math
import logging
logger = logging.getLogger(__name__)
from models import (
    PlanningPeriod, User, TeamQualificationType, DutyQualificationType,
    Duty, TeamDuty
)


def get_all_team_duty_qualification_types_as_dict(session):
    list_of_team_duty_qualification_types = session.query(TeamQualificationType).filter_by(institution_id=1).all()
    all_team_duty_qualification_types = dict()
    for dqt in list_of_team_duty_qualification_types:
        if dqt.team_type_id in all_team_duty_qualification_types.keys():
            all_team_duty_qualification_types[dqt.team_type_id].append({"qualification_id": dqt.qualification_id, "desired_value": dqt.desired_value, "is_soft": dqt.is_soft, "soft_weight": dqt.soft_weight})
        else:
            all_team_duty_qualification_types[dqt.team_type_id] = [{"qualification_id": dqt.qualification_id, "desired_value": dqt.desired_value, "is_soft": dqt.is_soft, "soft_weight": dqt.soft_weight}]
    return all_team_duty_qualification_types


def get_all_duty_qualification_types_as_dict(session):
    list_of_duty_qualification_types = session.query(DutyQualificationType).filter_by(institution_id=1).all()
    all_duty_qualification_types = dict()
    for dqt in list_of_duty_qualification_types:
        if dqt.duty_type_id in all_duty_qualification_types.keys():
            all_duty_qualification_types[dqt.duty_type_id].append({"qualification_id": dqt.qualification_id, "desired_value": dqt.desired_value, "is_soft": dqt.is_soft, "soft_weight": dqt.soft_weight})
        else:
            all_duty_qualification_types[dqt.duty_type_id] = [{"qualification_id": dqt.qualification_id, "desired_value": dqt.desired_value, "is_soft": dqt.is_soft, "soft_weight": dqt.soft_weight}]
    return all_duty_qualification_types


def get_duties_that_user_is_qualified_for(session, user_id, planning_period_id):
    planning_period = session.query(PlanningPeriod).filter_by(id=planning_period_id).first()
    user = session.query(User).filter_by(id=user_id).first()
    user_qualifications = user.qualifications_of_physician

    all_duty_qualification_types = get_all_duty_qualification_types_as_dict(session)
    duties_that_user_is_qualified_for = list()
    for duty in planning_period.duties_of_planning_period:
        add_duty = True
        if duty.duty_type in all_duty_qualification_types.keys():
            for dqt in all_duty_qualification_types[duty.duty_type]:
                try:
                    user_is_qualified = bool()
                    if dqt["desired_value"] and not dqt["is_soft"]:
                        user_is_qualified = False
                        for q in user_qualifications:
                            if q.qualification_id == dqt[
                                "qualification_id"] and q.date_from <= duty.time_start.date() and q.date_to >= duty.time_end.date():
                                user_is_qualified = True
                    elif not dqt["is_soft"]:
                        user_is_qualified = True
                        for q in user_qualifications:
                            if q.qualification_id == dqt[
                                "qualification_id"] and q.date_from <= duty.time_start.date() and q.date_to >= duty.time_end.date():
                                user_is_qualified = False

                    if dqt["is_soft"]:
                        user_is_qualified = True

                    if not user_is_qualified:
                        add_duty = False
                except KeyError as e:
                    logger.warning(f"Missing key in qualification requirement: {e}")
                    raise

        if add_duty:
            duties_that_user_is_qualified_for.append(duty)
    return duties_that_user_is_qualified_for


def get_duties_that_user_is_qualified_for_and_appropriate(session, user_id, planning_period_id):
    planning_period = session.query(PlanningPeriod).filter_by(id=planning_period_id).first()
    user = session.query(User).filter_by(id=user_id).first()
    user_qualifications = user.qualifications_of_physician

    all_duty_qualification_types = get_all_duty_qualification_types_as_dict(session)
    duties_that_user_is_qualified_for = list()
    for duty in planning_period.duties_of_planning_period:
        add_duty = True
        if duty.duty_type in all_duty_qualification_types.keys():
            for dqt in all_duty_qualification_types[duty.duty_type]:
                if dqt["desired_value"]:
                    user_is_qualified = False
                    for q in user_qualifications:
                        if q.qualification_id == dqt[
                            "qualification_id"] and q.date_from <= duty.time_start.date() and q.date_to >= duty.time_end.date():
                            user_is_qualified = True
                else:
                    user_is_qualified = True
                    for q in user_qualifications:
                        if q.qualification_id == dqt[
                            "qualification_id"] and q.date_from <= duty.time_start.date() and q.date_to >= duty.time_end.date():
                            user_is_qualified = False
                if not user_is_qualified:
                    add_duty = False

        if add_duty:
            duties_that_user_is_qualified_for.append(duty)
    return duties_that_user_is_qualified_for


def get_unsuitability(session, user_id, duty_id):
    duty = session.query(Duty).filter_by(id=duty_id).first()
    user = session.query(User).filter_by(id=user_id).first()
    user_qualifications = user.qualifications_of_physician

    all_duty_qualification_types = get_all_duty_qualification_types_as_dict(session)
    unsuitability = int()

    for dqt in all_duty_qualification_types[duty.duty_type]:
        if dqt["desired_value"]:
            user_is_qualified = False
            for q in user_qualifications:
                if q.qualification_id == dqt["qualification_id"] and q.date_from <= duty.time_start.date() and q.date_to >= duty.time_end.date():
                    user_is_qualified = True

        else:
            user_is_qualified = True
            for q in user_qualifications:
                if q.qualification_id == dqt["qualification_id"] and q.date_from <= duty.time_start.date() and q.date_to >= duty.time_end.date():
                    user_is_qualified = False

        if not user_is_qualified:
            if not dqt["is_soft"]:
                unsuitability = math.inf
            else:
                unsuitability += dqt["soft_weight"]

    return unsuitability


def get_team_duties_that_user_is_qualified_for_and_appropriate(session, user_id, planning_period_id):
    planning_period = session.query(PlanningPeriod).filter_by(id=planning_period_id).first()
    user = session.query(User).filter_by(id=user_id).first()
    user_qualifications = user.qualifications_of_physician

    all_team_qualification_types = get_all_team_duty_qualification_types_as_dict(session)
    team_duties_that_user_is_qualified_for = list()
    for team_duty in planning_period.team_duties_of_planning_period:
        add_duty = True
        if team_duty.team_type in all_team_qualification_types.keys():
            for dqt in all_team_qualification_types[team_duty.team_type]:
                if dqt["desired_value"]:
                    user_is_qualified = False
                    for q in user_qualifications:
                        if q.qualification_id == dqt[
                            "qualification_id"] and q.date_from <= team_duty.time_start.date() and q.date_to >= team_duty.time_end.date():
                            user_is_qualified = True
                else:
                    user_is_qualified = True
                    for q in user_qualifications:
                        if q.qualification_id == dqt[
                            "qualification_id"] and q.date_from <= team_duty.time_start.date() and q.date_to >= team_duty.time_end.date():
                            user_is_qualified = False
                if not user_is_qualified:
                    add_duty = False

        if add_duty:
            team_duties_that_user_is_qualified_for.append(team_duty)
    return team_duties_that_user_is_qualified_for


def get_team_duties_that_user_is_qualified_for(session, user_id, planning_period_id):
    planning_period = session.query(PlanningPeriod).filter_by(id=planning_period_id).first()
    user = session.query(User).filter_by(id=user_id).first()
    user_qualifications = user.qualifications_of_physician

    all_team_duty_qualification_types = get_all_team_duty_qualification_types_as_dict(session)
    team_duties_that_user_is_qualified_for = list()
    for team_duty in planning_period.team_duties_of_planning_period:
        add_team_duty = True
        if team_duty.team_type in all_team_duty_qualification_types.keys():
            for dqt in all_team_duty_qualification_types[team_duty.team_type]:
                try:
                    user_is_qualified = bool()
                    if dqt["desired_value"] and not dqt["is_soft"]:
                        user_is_qualified = False
                        for q in user_qualifications:
                            if q.qualification_id == dqt[
                                "qualification_id"] and q.date_from <= team_duty.time_start.date() and q.date_to >= team_duty.time_end.date():
                                user_is_qualified = True
                    elif not dqt["is_soft"]:
                        user_is_qualified = True
                        for q in user_qualifications:
                            if q.qualification_id == dqt[
                                "qualification_id"] and q.date_from <= team_duty.time_start.date() and q.date_to >= team_duty.time_end.date():
                                user_is_qualified = False

                    if dqt["is_soft"]:
                        user_is_qualified = True

                    if not user_is_qualified:
                        add_team_duty = False
                except KeyError as e:
                    print(f"ERROR: Missing key in qualification requirement: {e}")
                    print(f"Full dqt object: {dqt}")
                    raise

        if add_team_duty:
            team_duties_that_user_is_qualified_for.append(team_duty)
    return team_duties_that_user_is_qualified_for


def get_unsuitability_team_duty(session, user_id, team_duty_id):
    team_duty = session.query(TeamDuty).filter_by(id=team_duty_id).first()
    user = session.query(User).filter_by(id=user_id).first()
    user_qualifications = user.qualifications_of_physician

    all_team_duty_qualification_types = get_all_team_duty_qualification_types_as_dict(session)
    unsuitability = int()

    for dqt in all_team_duty_qualification_types[team_duty.team_type]:
        if dqt["desired_value"]:
            user_is_qualified = False
            for q in user_qualifications:
                if q.qualification_id == dqt["qualification_id"] and q.date_from <= team_duty.time_start.date() and q.date_to >= team_duty.time_end.date():
                    user_is_qualified = True

        else:
            user_is_qualified = True
            for q in user_qualifications:
                if q.qualification_id == dqt["qualification_id"] and q.date_from <= team_duty.time_start.date() and q.date_to >= team_duty.time_end.date():
                    user_is_qualified = False

        if not user_is_qualified:
            if not dqt["is_soft"]:
                unsuitability = math.inf
            else:
                unsuitability += dqt["soft_weight"]

    return unsuitability
