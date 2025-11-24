from datetime import timedelta, datetime, time as dt_time, date
import holidays
import mip
import time
import math
import calendar
from models import (
    DutyAdditionalPhysicianAssignment, PlanningPeriod, User, DutyPhysicianAssignment,
    TeamDutyBlock, TeamDutyPhysicianAssignment, Pool, TeamBlockType, DutyType,
    TeamType, Station, TeamDutyRestingTime, DutyTeamDutyRestingTime, DutyDutyRestingTime,
    AbsencePhysicians, DutyBlockType, DutyBlock, Weekend, PhysicianPool, PhysicianPreferencesWeekend,
    GeneralPreferencesConfiguration, DutyAbsences, TeamDutyAbsences, WeeklyWishesOfPhysicians,
    WeeklyBlockSpecificPreferences, WeeklyPreferenceToDutyAssignment, WeeklyWishesOfPhysiciansPerDuty,
    PreferencesForDaysOptionsConfiguration, ApplicationSettings
)

from utils import (
    get_duties_that_user_is_qualified_for,
    get_team_duties_that_user_is_qualified_for,
    get_unsuitability,
    get_team_duties_that_user_is_qualified_for_and_appropriate,
    get_duties_that_user_is_qualified_for_and_appropriate,
    get_unsuitability_team_duty,
)


class ipSolver():
    def __init__(self, input_data, session):
        self.session = session
        self.planning_period = input_data["planning_period"]
        users = session.query(User).filter_by(is_being_planned=1, is_active=1).all()
        users.sort(key=lambda x: x.last_name, reverse=False)
        self.pools = session.query(Pool).all()
        self.preference_weights = session.query(PreferencesForDaysOptionsConfiguration).all()
        self.team_block_types = session.query(TeamBlockType).all()
        self.duty_block_type = session.query(DutyBlockType).all()
        self.duty_blocks = session.query(DutyBlock).all()
        self.absences = session.query(AbsencePhysicians).all()
        self.team_duty_types = session.query(TeamType).all()
        self.team_duty_blocks = session.query(TeamDutyBlock).all()
        self.weekly_wishes = session.query(WeeklyWishesOfPhysicians).filter_by(planning_period_id=self.planning_period.id).all()
        self.weekly_preferences_to_duty_assignments = session.query(WeeklyPreferenceToDutyAssignment).all()
        self.add_duty_assignments = session.query(DutyAdditionalPhysicianAssignment).filter_by(planning_period_id=self.planning_period.id).all()
        self.team_duty_resting_time = session.query(TeamDutyRestingTime).all()
        self.duty_team_duty_resting_time = session.query(DutyTeamDutyRestingTime).all()
        self.duty_duty_resting_time = session.query(DutyDutyRestingTime).all()
        self.stations = session.query(Station).all()
        self.duty_types = session.query(DutyType).all()
        self.list_of_physicians = users
        self.duty_physician_assignment = session.query(DutyPhysicianAssignment).all()
        self.physician_pool = session.query(PhysicianPool).all()
        self.team_duty_physician_assignment = session.query(TeamDutyPhysicianAssignment).all()
        self.all_planning_periods = session.query(PlanningPeriod).all()
        self.weekend = session.query(Weekend).all()[0]
        self.preferences_weekend = session.query(PhysicianPreferencesWeekend).all()
        self.general_preferences_configuration = session.query(GeneralPreferencesConfiguration).all()[0]
        self.duty_absences = session.query(DutyAbsences).all()
        self.team_duty_absences = session.query(TeamDutyAbsences).all()
        print("created solver")

    def solve(self):
        start_time = time.time()
        solver_name = mip.CBC
        m = mip.Model(sense=mip.MAXIMIZE, solver_name=solver_name)
        print("solver.solve triggered")

        weekend_time_start = self.weekend.start_time
        weekend_time_end = self.weekend.end_time

        max_consecutive_weekends = self.session.query(Weekend).all()[0].max_consecutive_weekends
        max_number_weekends_per_month = self.session.query(Weekend).all()[0].max_number_weekends_per_month
        min_free_weekends_per_month = self.session.query(Weekend).all()[0].min_free_weekends_per_month
        min_free_weekends_per_month_soft = self.session.query(Weekend).all()[0].min_free_weekends_per_month_soft

        previous_planning_period = None
        previous_planning_period_list = [x for x in self.all_planning_periods if x.id == self.planning_period.previous_planning_period_id]
        if len(previous_planning_period_list) > 0:
            previous_planning_period = previous_planning_period_list[0]

        months_ = []

        # calculate the last duty of the planning period
        last_duty_of_pp = max([d.time_end for d in self.planning_period.duties_of_planning_period])
        last_team_duty_of_pp = max([td.time_end for td in self.planning_period.team_duties_of_planning_period], default=None)
        if last_team_duty_of_pp is None:
            last_date_of_pp = last_duty_of_pp.date()
        else:
            last_date_of_pp = max(last_duty_of_pp, last_team_duty_of_pp).date()
        current_date = self.planning_period.date_from
        while current_date <= last_date_of_pp:
            months_.append((current_date.month, current_date.year))

            if current_date.month == 12:
                current_date = date(current_date.year + 1, 1, 1)
            else:
                current_date = date(current_date.year, current_date.month + 1, 1)


        # tuples of weekends with first and last day of weekend
        weekends_ = []

        def get_weekends(weekends, planning_period):
            # get first day which is at a weekend and respective last day of that weekend
            first_weekend_day = None
            last_weekend_day = None
            for i in range((planning_period.date_to - planning_period.date_from).days + 1):
                if (planning_period.date_from + timedelta(days=i)).weekday() == 4:
                    first_weekend_day = datetime.combine(planning_period.date_from + timedelta(days=i), weekend_time_start)
                    if planning_period.date_from + timedelta(days=i + 3) <= planning_period.date_to:
                        last_weekend_day = datetime.combine(planning_period.date_from + timedelta(days=i + 3), weekend_time_end)
                    else:
                        last_weekend_day = datetime.combine(planning_period.date_to, dt_time(23, 59))
                    break
                if (planning_period.date_from + timedelta(days=i)).weekday() == 5:
                    first_weekend_day = datetime.combine(planning_period.date_from + timedelta(days=i), dt_time(0, 0))
                    if planning_period.date_from + timedelta(days=i + 2) <= planning_period.date_to:
                        last_weekend_day = datetime.combine(planning_period.date_from + timedelta(days=i + 2), weekend_time_end)
                    else:
                        last_weekend_day = datetime.combine(planning_period.date_to, dt_time(23, 59))
                    break
                if (planning_period.date_from + timedelta(days=i)).weekday() == 6:
                    first_weekend_day = datetime.combine(planning_period.date_from + timedelta(days=i), dt_time(0, 0))
                    if planning_period.date_from + timedelta(days=i+1) <= planning_period.date_to:
                        last_weekend_day = datetime.combine(planning_period.date_from + timedelta(days=i+1), weekend_time_end)
                    else:
                        last_weekend_day = datetime.combine(planning_period.date_to, dt_time(23, 59))
                    break

            weekends.append((first_weekend_day, last_weekend_day))

            # get last duty of planning period
            last_duty = max([d.time_end for d in planning_period.duties_of_planning_period], default=None)
            last_team_duty = max([td.time_end for td in planning_period.team_duties_of_planning_period], default=None)
            last_time = max([t for t in [last_duty, last_team_duty] if t is not None], default=None)

            for i in range((last_time.date() - planning_period.date_from).days + 1):
                if datetime.combine((weekends[-1][1] + timedelta(days=4)).date(), weekend_time_start) <= last_time:
                    start = datetime.combine((weekends[-1][1] + timedelta(days=4)).date(), weekend_time_start)
                else:
                    break
                if datetime.combine((weekends[-1][1] + timedelta(days=7)).date(), weekend_time_end) <= last_time:
                    end = datetime.combine((weekends[-1][1] + timedelta(days=7)).date(), weekend_time_end)
                else:
                    end = datetime.combine(last_time.date(), dt_time(23, 59))

                weekends.append((start, end))

                if end.weekday() != 0:
                    break

        get_weekends(weekends_, self.planning_period)

        def saturday_of_weekend(weekend):
            if weekend[0].weekday() == 5:
                return weekend[0]
            elif weekend[1].weekday() == 5:
                return weekend[1]
            return weekend[0] + timedelta(days=1)


        weekends_of_month = {month: [w for w in weekends_ if (saturday_of_weekend(w).month, saturday_of_weekend(w).year) == month] for month in months_}

        duties_of_weekend = {w: [d for d in self.planning_period.duties_of_planning_period
                                 if d.time_start < w[1] and d.time_end > w[0]]
                             for w in weekends_}

        team_duties_of_weekend = {w: [td for td in self.planning_period.team_duties_of_planning_period
                                      if td.time_start < w[1] and td.time_end > w[0]]
                                  for w in weekends_}


        # VARIABLES
        duty_assignment = {
            (p, d): m.add_var(
                name="duty_assignment_({},{})".format(p, d),
                var_type=mip.BINARY,
                lb=0,
                ub=1,
            )
            for p in self.list_of_physicians
            for d in self.planning_period.duties_of_planning_period
        }

        shift_assignment = {
            (p, s): m.add_var(
                name="shift_assignment_({},{},{})".format(p.last_name, s.name, s.time_start),
                var_type=mip.BINARY,
                lb=0,
                ub=1,
            )
            for p in self.list_of_physicians
            for s in self.planning_period.team_duties_of_planning_period
        }

        desired_shift_assignment = {
            s: m.add_var(
                name="desired_shift_assignment_({})".format(s),
                var_type=mip.INTEGER,
                lb=0,
                ub=next(x for x in self.team_duty_types if x.id == s.team_type).desired_number_of_physicians - next(x for x in self.team_duty_types if x.id == s.team_type).number_of_required_physicians,
            )
            for s in self.planning_period.team_duties_of_planning_period
        }

        max_shift_assignment = {
            s: m.add_var(
                name="max_shift_assignment_({})".format(s),
                var_type=mip.INTEGER,
                lb=0,
                ub=max(0, next(x for x in self.team_duty_types if x.id == s.team_type).desired_number_of_physicians_2 - next(x for x in self.team_duty_types if x.id == s.team_type).desired_number_of_physicians),
            )
            for s in self.planning_period.team_duties_of_planning_period
        }

        auxiliary_shift_assignment = {
            s: m.add_var(
                name="auxiliary_shift_assignment_({})".format(s),
                var_type=mip.BINARY,
                lb=0,
            )
            for s in self.planning_period.team_duties_of_planning_period
        }

        duty_block_assignment = {
            (a, b): m.add_var(
                name="duty_block_assignment_({},{})".format(a, b),
                var_type=mip.BINARY,
                lb=0,
                ub=1,
            )
            for a in self.list_of_physicians
            for b in self.planning_period.duty_blocks_of_planning_period
        }

        shift_block_assignment = {
            (a, b): m.add_var(
                name="shift_block_assignment_({},{})".format(a, b),
                var_type=mip.BINARY,
                lb=0,
                ub=1,
            )
            for a in self.list_of_physicians
            for b in self.planning_period.team_duty_blocks_of_planning_period
        }

        consecutive_shift_block_assignment = {
            (p, tdb): m.add_var(
                name="consecutive_shift_block_assignment_({},{})".format(p, tdb),
                var_type=mip.BINARY,
                lb=0,
                ub=1,
            )
            for p in self.list_of_physicians
            for tdb in [bl
                        for td_block_type in [x for x in self.team_block_types if x.consecutive_assignment]
                        for bl in self.planning_period.team_duty_blocks_of_planning_period
                        if bl.team_block_type == td_block_type.id]
        }

        consecutive_duty_assignment = {
            (p, d): m.add_var(
                name="consecutive_duty_assignment_({},{})".format(p, d),
                var_type=mip.BINARY,
                lb=0,
                ub=1,
            )
            for p in self.list_of_physicians
            for d in self.planning_period.duties_of_planning_period
        }

        duty_duty_desired_rest_time_list = []

        for ddrt in [x for x in self.duty_duty_resting_time if x.resting_time_desired >= 0]:
            for d1 in [x for x in self.planning_period.duties_of_planning_period if x.duty_type == ddrt.duty_type_id]:
                for d2 in [x for x in self.planning_period.duties_of_planning_period if
                           x.duty_type == ddrt.following_duty_type_id
                           and d1.time_start <= x.time_start < d1.time_end + timedelta(
                               hours=ddrt.resting_time_desired) and x != d1]:
                    duty_duty_desired_rest_time_list.append((d1, d2, ddrt.weight_resting_time))

        desired_rest_time_duties = {
            (p, duties[0], duties[1]): m.add_var(
                name="duty_duty_desired_rest_time_({},{},{})".format(p, duties[0], duties[1]),
                var_type=mip.BINARY,
                lb=0,
            )
            for p in self.list_of_physicians
            for duties in duty_duty_desired_rest_time_list
        }

        duty_shift_desired_rest_time_list = []

        for dtdrt in [x for x in self.duty_team_duty_resting_time if x.resting_time_desired >= 0]:
            for d1 in [x for x in self.planning_period.duties_of_planning_period if x.duty_type == dtdrt.duty_type_id]:
                for d2 in [x for x in self.planning_period.team_duties_of_planning_period if
                           d1.time_start <= x.time_start < d1.time_end + timedelta(
                               hours=dtdrt.resting_time_desired) and x != d1]:
                    duty_shift_desired_rest_time_list.append((d1, d2, dtdrt.weight_resting_time))

        desired_rest_time_duty_shift = {
            (p, d1, d2): m.add_var(
                name="duty_shift_desired_rest_time_({},{},{})".format(p, d1, d2),
                var_type=mip.BINARY,
                lb=0,
            )
            for p in self.list_of_physicians
            for dtdrt in self.duty_team_duty_resting_time
            for d1 in [x for x in self.planning_period.duties_of_planning_period if x.duty_type == dtdrt.duty_type_id]
            for d2 in [x for x in self.planning_period.team_duties_of_planning_period
                       if d1.time_start <= x.time_start < d1.time_end + timedelta(hours=dtdrt.resting_time_desired)]
            }

        shift_duty_desired_rest_time_list = []

        for tddrt in [x for x in self.team_duty_resting_time if x.resting_time_desired >= 0]:
            for d1 in [x for x in self.planning_period.team_duties_of_planning_period if x.team_type == tddrt.team_type_id]:
                for d2 in [x for x in self.planning_period.duties_of_planning_period if
                           d1.time_start <= x.time_start < d1.time_end + timedelta(
                               hours=tddrt.resting_time_desired) and x != d1]:
                    shift_duty_desired_rest_time_list.append((d1, d2, tddrt.weight_resting_time))

        desired_rest_time_shift_duty = {
            (p, d1, d2): m.add_var(
                name="shift_duty_desired_rest_time_({},{},{})".format(p, d1, d2),
                var_type=mip.BINARY,
                lb=0,
            )
            for p in self.list_of_physicians
            for tddrt in self.team_duty_resting_time
            for d1 in [x for x in self.planning_period.team_duties_of_planning_period if x.team_type == tddrt.team_type_id]
            for d2 in [x for x in self.planning_period.duties_of_planning_period
                       if d1.time_start <= x.time_start < d1.time_end + timedelta(hours=tddrt.resting_time_desired)]
            }

        shift_shift_desired_rest_time_list = []

        for tdtdrt in [x for x in self.team_duty_resting_time if x.resting_time_desired_team >= 0]:
            for d1 in [x for x in self.planning_period.team_duties_of_planning_period if x.team_type == tdtdrt.team_type_id]:
                for d2 in [x for x in self.planning_period.team_duties_of_planning_period if
                           d1.time_start <= x.time_start < d1.time_end + timedelta(
                               hours=tdtdrt.resting_time_desired_team) and x != d1]:
                    shift_shift_desired_rest_time_list.append((d1, d2, tdtdrt.weight_resting_time))

        desired_rest_time_shifts = {
            (p, d1, d2): m.add_var(
                name="Soft_Resting_Time4({},{},{})".format(p, d1, d2),
                var_type=mip.BINARY,
                lb=0,
            )
            for p in self.list_of_physicians
            for tdtdrt in self.team_duty_resting_time
            for d1 in [x for x in self.planning_period.team_duties_of_planning_period if x.team_type == tdtdrt.team_type_id]
            for d2 in [x for x in self.planning_period.team_duties_of_planning_period
                       if d1.time_start <= x.time_start < d1.time_end + timedelta(hours=tdtdrt.resting_time_desired_team)]
            }

        weekend_attendance = {
            (p, w): m.add_var(
                name="weekend_attendance_({},{})".format(p, w),
                var_type=mip.BINARY,
                lb=0,
            )
            for p in self.list_of_physicians
            for w in weekends_
        }

        weekend_preference_violation = {
            (p, w): m.add_var(
                name="weekend_preference_violation_({},{})".format(p, w),
                var_type=mip.INTEGER,
                lb=0,
            )
            for p in self.list_of_physicians
            for w in weekends_
        }

        max_weekend_violation = {
            (p, i): m.add_var(
                name="max_weekend_violation_({},{})".format(p, i),
                var_type=mip.INTEGER,
                lb=0,
            )
            for p in self.list_of_physicians
            for i in months_
        }

        min_free_weekend_violation = {
            (p, i): m.add_var(
                name="min_free_weekend_violation_({},{})".format(p, i),
                var_type=mip.INTEGER,
                lb=0,
            )
            for p in self.list_of_physicians
            for i in months_
        }

        max_number_of_duties_violation = {
            (pool, p): m.add_var(
                name="max_number_of_duties_violation_({},{})".format(pool, p),
                var_type=mip.INTEGER,
                lb=0,
            )
            for pool in [x for x in self.pools if x.maximal_number_of_duties_soft is True]
            for p in [x for x in self.list_of_physicians if x.id in [a.physician_id for a in pool.physicians_that_have_pool if a.date_from <= self.planning_period.date_from and a.date_to >= self.planning_period.date_to]]
        }

        min_number_of_duties_violation = {
            (pool, p): m.add_var(
                name="min_number_of_duties_violation_({},{})".format(pool, p),
                var_type=mip.INTEGER,
                lb=0,
            )
            for pool in [x for x in self.pools if x.minimal_number_of_duties_soft is True]
            for p in [x for x in self.list_of_physicians if x.id in [a.physician_id for a in pool.physicians_that_have_pool if a.date_from <= self.planning_period.date_from and a.date_to >= self.planning_period.date_to]]
        }

        max_number_of_physicians_violation = {
            (pool, i): m.add_var(
                name="max_number_of_physicians_violation_({},{})".format(pool, i),
                var_type=mip.INTEGER,
                lb=0,
            )
            for pool in [x for x in self.pools if x.maximal_number_of_physicians_soft is True]
            for i in range((self.planning_period.date_to - self.planning_period.date_from).days + 1)
        }

        deviation_duties_pool_neg = {
            (p, phy): m.add_var(
                name="deviation_duties_pool_neg_({},{})".format(p, phy),
                var_type=mip.CONTINUOUS,
                lb=0,
            )
            for p in self.pools if p.fair_distribution
            for phy in self.list_of_physicians if phy.id in [a.physician_id for a in p.physicians_that_have_pool]
        }

        deviation_duties_pool_pos = {
            (p, phy): m.add_var(
                name="deviation_duties_pool_pos_({},{})".format(p, phy),
                var_type=mip.CONTINUOUS,
                lb=0,
            )
            for p in self.pools if p.fair_distribution
            for phy in self.list_of_physicians if phy.id in [a.physician_id for a in p.physicians_that_have_pool]
        }

        max_cons_shift_violation = {
            b: m.add_var(
                name="max_cons_shift_violation({})".format(b),
                var_type=mip.BINARY,
                lb=0,
            )
            for b in self.planning_period.team_duty_blocks_of_planning_period
        }



    # CONSTRAINTS


    # DUTY ASSIGNMENT

        # all additional duty assignments
        # (this is just if new physicians are additionally assigned to a duty, to learn from the experienced physician)
        add_duty_assignment_ids = [x.duty_id for x in self.add_duty_assignments]

        number_of_duty_assignments = {}
        for duty_id in add_duty_assignment_ids:
            additional_duty_assignments = [x for x in self.add_duty_assignments if x.duty_id == duty_id]
            number_of_duty_assignments[duty_id] = len(additional_duty_assignments)

        duties_in_a_duty_block = [duty for block in self.planning_period.duty_blocks_of_planning_period for duty in block.duties_of_duty_block]
        copy_add_duty_assignment_ids = add_duty_assignment_ids
        for duty in [x for x in self.planning_period.duties_of_planning_period if x.id in copy_add_duty_assignment_ids and x in duties_in_a_duty_block]:
            if number_of_duty_assignments[duty.id] > 0:
                duty_block = [x for x in self.planning_period.duty_blocks_of_planning_period if duty in x.duties_of_duty_block][0]
                add_duty_assignment_ids += [x.id for x in duty_block.duties_of_duty_block]
                for other_duty_id in [x.id for x in duty_block.duties_of_duty_block]:
                    number_of_duty_assignments[other_duty_id] = number_of_duty_assignments[duty.id]

        # mandatory duty is assigned to a physician (As the next constraint, but adjusted, if additional physicians are assigned to a duty)
        for d in [x for x in self.planning_period.duties_of_planning_period if x.id in add_duty_assignment_ids]:
            m += mip.xsum(duty_assignment[p, d] for p in self.list_of_physicians) == number_of_duty_assignments[d.id] + 1, "mandatory_add_duty_{}".format(d)

        # mandatory duty is assigned to a physician
        for d in [x for x in self.planning_period.duties_of_planning_period if [i for i in self.duty_types if i.id == x.duty_type][0].mandatory and x.id not in add_duty_assignment_ids]:
            m += mip.xsum(duty_assignment[p, d] for p in self.list_of_physicians) == 1, "mandatory_duty_{}".format(d)

        # non-mandatory duty is assigned to at most one physician
        for d in [x for x in self.planning_period.duties_of_planning_period if x.id not in add_duty_assignment_ids]:
            m += mip.xsum(duty_assignment[p, d] for p in self.list_of_physicians) <= 1, "max_one_duty_{}".format(d)

        # manually assigned duties
        for dpa in [x for x in self.duty_physician_assignment if x.fixed_assignment]:
            d = next((x for x in self.planning_period.duties_of_planning_period if x.id == dpa.duty_id), None)
            p = next((x for x in self.list_of_physicians if x.id == dpa.user_id), None)
            if d is not None and p is not None:
                m += duty_assignment[p, d] == 1, "fixed_duty_{}_{}".format(p, d)

        # additionally assigned physicians to duties
        for adpa in [x for x in self.add_duty_assignments]:
            d = next((x for x in self.planning_period.duties_of_planning_period if x.id == adpa.duty_id), None)
            p = next((x for x in self.list_of_physicians if x.id == adpa.user_id), None)
            if d is not None and p is not None:
                m += duty_assignment[p, d] == 1, "add_fixed_duty_{}_{}".format(p, d)

        # manually planned physicians only get their manually planned duties
        for p in [x for x in self.list_of_physicians if x.planned_manually]:
            dpa = [x.duty_id for x in self.duty_physician_assignment if x.user_id == p.id and x.fixed_assignment and x.planning_period_id == self.planning_period.id]
            dpa_copy = dpa.copy()
            for duty_id in dpa_copy:
                duty = next(x for x in self.planning_period.duties_of_planning_period if x.id == duty_id)
                duty_block = next((x for x in self.planning_period.duty_blocks_of_planning_period if duty in x.duties_of_duty_block), None)
                if duty_block is not None:
                    dpa += [x.id for x in duty_block.duties_of_duty_block]

            duties_not_in_dpa = [x for x in self.planning_period.duties_of_planning_period if x.id not in dpa]
            m += mip.xsum(duty_assignment[p, d] for d in duties_not_in_dpa) == 0, "manual_duty_{}".format(p)


    # SHIFT ASSIGNMENT

        number_of_manual_assignments = {}
        add_team_duty_ids = []
        for td in self.planning_period.team_duties_of_planning_period:
            team_type = next(x for x in self.team_duty_types if x.id == td.team_type)
            if team_type.desired_number_of_physicians_2 < len([x for x in self.team_duty_physician_assignment if x.team_duty_id == td.id and x.fixed_assignment]):
                number_of_manual_assignments[td.id] = len([x for x in self.team_duty_physician_assignment if x.team_duty_id == td.id and x.fixed_assignment])
                add_team_duty_ids.append(td.id)

        team_duties_in_a_duty_block = [td for block in self.planning_period.team_duty_blocks_of_planning_period for td in block.team_duties_of_team_block]
        copy_add_team_duty_ids = add_team_duty_ids
        for td in [x for x in self.planning_period.team_duties_of_planning_period if x.id in copy_add_team_duty_ids and x in team_duties_in_a_duty_block]:
            team_type = next(x for x in self.team_duty_types if x.id == td.team_type)
            if number_of_manual_assignments[td.id] > team_type.desired_number_of_physicians_2:
                team_duty_block = [x for x in self.planning_period.team_duty_blocks_of_planning_period if td in x.team_duties_of_team_block][0]
                add_team_duty_ids += [x.id for x in team_duty_block.team_duties_of_team_block]
                for other_team_duty_id in [x.id for x in team_duty_block.team_duties_of_team_block]:
                    number_of_manual_assignments[other_team_duty_id] = number_of_manual_assignments[td.id]

        for td in [x for x in self.planning_period.team_duties_of_planning_period if x.id not in add_team_duty_ids]:
            team_type = next(x for x in self.team_duty_types if x.id == td.team_type)
            number_of_manual_assignments[td.id] = team_type.desired_number_of_physicians_2

        # Each shift has minimum and maximum number of physicians assigned
        for td in self.planning_period.team_duties_of_planning_period:
            team_type = next(x for x in self.team_duty_types if x.id == td.team_type)
            if number_of_manual_assignments[td.id] <= team_type.desired_number_of_physicians_2:
                station_id = next(x.id for x in self.stations if x.id == team_type.station_id)
                physicians_in_station = [x for x in self.list_of_physicians if station_id in [s.station_id for s in x.stations_of_physician]]
                m += mip.xsum(shift_assignment[p, td] for p in physicians_in_station) >= team_type.number_of_required_physicians, "shift_1_{}".format(td.id)
                m += mip.xsum(shift_assignment[p, td] for p in physicians_in_station) <= team_type.desired_number_of_physicians_2, "shift_2_{}".format(td)

                # desired_shift_assignment[td] and max_shift_assignment[td] equals the number of
                # physicians assigned beyond the required minimum
                m += mip.xsum(shift_assignment[p, td] for p in physicians_in_station) - desired_shift_assignment[td] - max_shift_assignment[td] == team_type.number_of_required_physicians, "shift_3_{}".format(td)

                # max_shift_assignment[td] can take a positive value
                # only if desired_shift_assignment[td] is at its upper bound
                m += team_type.desired_number_of_physicians_2 * auxiliary_shift_assignment[td] + desired_shift_assignment[td] >= (team_type.desired_number_of_physicians - team_type.number_of_required_physicians), "shift_4_{}".format(td)
                m += max_shift_assignment[td] + team_type.desired_number_of_physicians_2 * auxiliary_shift_assignment[td] <= team_type.desired_number_of_physicians_2, "shift_5_{}".format(td)

                # Only physicians from the corresponding ward can be assigned to the shift
                m += mip.xsum(shift_assignment[p, td] for p in [x for x in self.list_of_physicians if x not in physicians_in_station]) == 0, "shift_6_{}".format(td)

        # manually assigned shifts
        for tdpa in [x for x in self.team_duty_physician_assignment if x.fixed_assignment]:
            td = next((x for x in self.planning_period.team_duties_of_planning_period if x.id == tdpa.team_duty_id), None)
            p = next((x for x in self.list_of_physicians if x.id == tdpa.user_id), None)
            if td is not None and p is not None:
                m += shift_assignment[p, td] == 1, "fixed_shift_{}_{}".format(p, td)

        # manually planned physicians only get their manually planned shifts
        for p in [x for x in self.list_of_physicians if x.planned_manually]:
            tdpa = [x.team_duty_id for x in self.team_duty_physician_assignment if x.user_id == p.id and x.fixed_assignment]
            team_duties_not_in_dpa = [x for x in self.planning_period.team_duties_of_planning_period if x.id not in tdpa]
            m += mip.xsum(shift_assignment[p, td] for td in team_duties_not_in_dpa) == 0, "manual_shift_{}".format(p)


    # ABSENCES

        duty_absences_of_physician = {p: [] for p in self.list_of_physicians}

        # no shift on absent days
        for a in self.absences:
            list_of_td = [x for x in self.planning_period.team_duties_of_planning_period if x.time_start.date() == a.day]
            physician = next((p for p in self.list_of_physicians if p.id == a.user_id), None)
            if physician is not None and len(list_of_td) > 0:
                m += mip.xsum(shift_assignment[physician, td] for td in list_of_td) == 0, "absence_shift_{}".format(a.id)

            # no duty on absent days
            list_of_d = [x for x in self.planning_period.duties_of_planning_period if x.time_start.date() == a.day]
            if physician is not None and len(list_of_d) > 0:
                m += mip.xsum(duty_assignment[physician, d] for d in list_of_d) == 0, "absence_duty_{}".format(a.id)

                duty_absences_of_physician[physician].extend(list_of_d)

        # no impossible duties
        for absence in self.duty_absences:
            duty = next((x for x in self.planning_period.duties_of_planning_period if x.id == absence.duty_id), None)
            physician = next((x for x in self.list_of_physicians if x.id == absence.user_id), None)
            if duty is not None and physician is not None:
                m += duty_assignment[physician, duty] == 0, "duty_impossible_{}_{}".format(physician, duty)

                duty_absences_of_physician[physician].append(duty)

        # no impossible shifts
        for absence in self.team_duty_absences:
            team_duty = next((x for x in self.planning_period.team_duties_of_planning_period if x.id == absence.team_duty_id), None)
            physician = next((x for x in self.list_of_physicians if x.id == absence.user_id), None)
            if team_duty is not None and physician is not None:
                m += shift_assignment[physician, team_duty] == 0, "shift_impossible_{}_{}".format(physician, team_duty)

        # duties on days before absence
        for a in self.absences:
            physician = next((x for x in self.list_of_physicians if x.id == a.user_id), None)
            list_of_d = [x for x in self.planning_period.duties_of_planning_period if x.time_start.date() == a.day - timedelta(days=1)]
            list_of_d = [d for d in list_of_d if not next(x for x in self.duty_types if x.id == d.duty_type).before_absence]
            if physician is not None:
                m += mip.xsum(duty_assignment[physician, d] for d in list_of_d) == 0, "before_absence_duty_{}".format(a.id)
                duty_absences_of_physician[physician].extend(list_of_d)

        # duties on days after absence
        for a in self.absences:
            physician = next((x for x in self.list_of_physicians if x.id == a.user_id), None)
            list_of_d = [x for x in self.planning_period.duties_of_planning_period if x.time_start.date() == a.day + timedelta(days=1)]
            list_of_d = [d for d in list_of_d if not next(x for x in self.duty_types if x.id == d.duty_type).after_absence]
            if physician is not None and len(list_of_d) > 0:
                m += mip.xsum(duty_assignment[physician, d] for d in list_of_d) == 0, "after_absence_duty_{}".format(a.id)
                duty_absences_of_physician[physician].extend(list_of_d)


    # SHIFT- AND DUTY BLOCKS

        # duties within a duty block are assigned to the same physician
        for p in self.list_of_physicians:
            for db in self.planning_period.duty_blocks_of_planning_period:
                # check if physician is manually assigned to a duty in the block
                absent_duties = []
                if len([x for x in self.duty_physician_assignment if x.user_id == p.id and x.fixed_assignment and x.planning_period_id == self.planning_period.id and x.duty_id in [d.id for d in db.duties_of_duty_block]]) > 0 \
                        or len([x for x in self.add_duty_assignments if x.user_id == p.id and x.planning_period_id == self.planning_period.id and x.duty_id in [d.id for d in db.duties_of_duty_block]]) > 0:
                    # check if other physician is manually assigned to a duty in the block
                    if len([x for x in self.duty_physician_assignment if x.user_id != p.id and x.fixed_assignment and x.planning_period_id == self.planning_period.id and x.duty_id in [d.id for d in db.duties_of_duty_block]]) > 0:
                        continue
                    # search for absent duties in this block of that physician
                    for a in [x for x in self.absences if x.user_id == p.id]:
                        absent_duties += [x for x in self.planning_period.duties_of_planning_period if x.time_start.date() == a.day]

                for d in [x for x in db.duties_of_duty_block if x not in absent_duties]:
                    m += duty_assignment[p, d] - duty_block_assignment[p, db] == 0, "duty_block_assignment_{}_{}".format(p, db)


        # shifts within a shift block are assigned to the same physician
        for p in self.list_of_physicians:
            for bl in self.planning_period.team_duty_blocks_of_planning_period:
                # check if physician is manually assigned to a team duty in the block
                absent_team_duties = []
                if len([x for x in self.team_duty_physician_assignment if x.user_id == p.id and x.fixed_assignment and x.planning_period_id == self.planning_period.id and x.team_duty_id in [td.id for td in bl.team_duties_of_team_block]]) > 0:
                    # check if other physician is manually assigned to a team duty in the block
                    if len([x for x in self.team_duty_physician_assignment if x.user_id != p.id and x.fixed_assignment and x.planning_period_id == self.planning_period.id and x.team_duty_id in [td.id for td in bl.team_duties_of_team_block]]) > 0:
                        continue
                    # search for absent team duties in this block of that physician
                    for a in [x for x in self.absences if x.user_id == p.id]:
                        absent_team_duties += [x for x in self.planning_period.team_duties_of_planning_period if x.time_start.date() == a.day]

                for td in [x for x in bl.team_duties_of_team_block if x not in absent_team_duties]:
                    m += shift_assignment[p, td] - shift_block_assignment[p, bl] == 0, "shift_block_assignment_{}_{}".format(p, bl)


        # free days after duty block
        for db in [x for x in self.planning_period.duty_blocks_of_planning_period if len(x.duties_of_duty_block) > 0]:
            dbt = next(x for x in self.duty_block_type if db.id in [y.id for y in x.blocks_of_duty_block_type])
            end_of_db = max(db.duties_of_duty_block, key=lambda duty: duty.time_start).time_start.date()
            for p in self.list_of_physicians:
                # no shifts within the free days
                for td in [x for x in self.planning_period.team_duties_of_planning_period if
                           end_of_db < x.time_start.date() <= end_of_db + timedelta(days=dbt.free_days_after_block)]:
                    m += shift_assignment[p, td] + duty_block_assignment[p, db] <= 1, "free_days_after_duty_block_{}_{}".format(p, db)

                # no duties within the free days
                for d in [x for x in self.planning_period.duties_of_planning_period if
                          end_of_db < x.time_start.date() <= end_of_db + timedelta(days=dbt.free_days_after_block)]:
                    m += duty_assignment[p, d] + duty_block_assignment[p, db] <= 1, "free_days_after_duty_block_{}_{}".format(p, db)

        # free days after duty blocks of previous planning period
        if previous_planning_period is not None:
            for db in previous_planning_period.duty_blocks_of_planning_period:
                dbt = next(x for x in self.duty_block_type if db in x.blocks_of_duty_block_type)
                if len(db.duties_of_duty_block) > 0:
                    end_of_db = max(db.duties_of_duty_block, key=lambda duty: duty.time_start).time_start.date()
                    physicians_of_db = [p for p in self.list_of_physicians if p.id in [x.user_id for x in self.duty_physician_assignment if x.duty_id == db.duties_of_duty_block[0].id]]
                    for p in physicians_of_db:
                        for td in [x for x in self.planning_period.team_duties_of_planning_period if
                                   end_of_db < x.time_start.date() <= end_of_db + timedelta(days=dbt.free_days_after_block)]:
                            m += shift_assignment[p, td] == 0, "free_days_after_duty_block_{}_{}".format(p, db)

                        for d in [x for x in self.planning_period.duties_of_planning_period if
                                  end_of_db < x.time_start.date() <= end_of_db + timedelta(days=dbt.free_days_after_block)]:
                            m += duty_assignment[p, d] == 0, "free_days_after_duty_block_{}_{}".format(p, db)


        # free days after shift block
        for tdb in [x for x in self.planning_period.team_duty_blocks_of_planning_period if len(x.team_duties_of_team_block) > 0]:
            tbt = next(x for x in self.team_block_types if tdb.id in [y.id for y in x.blocks_of_team_block_type])
            end_of_tdb = max(tdb.team_duties_of_team_block, key=lambda team_duty: team_duty.time_end).time_end
            for p in self.list_of_physicians:
                for td in [x for x in self.planning_period.team_duties_of_planning_period if
                           end_of_tdb <= x.time_start <= end_of_tdb + timedelta(days=tbt.free_days_after_block)]:
                    m += shift_assignment[p, td] + shift_block_assignment[p, tdb] <= 1, "free_days_after_shift_block_{}_{}".format(p, tdb)

                for d in [x for x in self.planning_period.duties_of_planning_period if
                          end_of_tdb <= x.time_start <= end_of_tdb + timedelta(days=tbt.free_days_after_block)]:
                    m += duty_assignment[p, d] + shift_block_assignment[p, tdb] <= 1, "free_days_after_shift_block_{}_{}".format(p, tdb)

        # free days after shift block of previous planning period
        if previous_planning_period is not None:
            for tdb in [x for x in previous_planning_period.team_duty_blocks_of_planning_period if len(x.team_duties_of_team_block) > 0]:
                tbt = next(x for x in self.team_block_types if tdb in x.blocks_of_team_block_type)
                end_of_tdb = max(tdb.team_duties_of_team_block, key=lambda team_duty: team_duty.time_end).time_end
                physicians_of_tdb = [p for p in self.list_of_physicians if p.id in [x.user_id for x in self.team_duty_physician_assignment if x.team_duty_id == tdb.team_duties_of_team_block[0].id]]
                for p in physicians_of_tdb:
                    for td in [x for x in self.planning_period.team_duties_of_planning_period if
                               end_of_tdb <= x.time_start <= end_of_tdb + timedelta(days=tbt.free_days_after_block)]:
                        m += shift_assignment[p, td] == 0, "free_days_after_shift_block_{}_{}".format(p, tdb)

                    for d in [x for x in self.planning_period.duties_of_planning_period if
                              end_of_tdb <= x.time_start <= end_of_tdb + timedelta(days=tbt.free_days_after_block)]:
                        m += duty_assignment[p, d] == 0, "free_days_after_shift_block_{}_{}".format(p, tdb)


        # No additional duties during duty block
        for p in self.list_of_physicians:
            for db in [x for x in self.planning_period.duty_blocks_of_planning_period if len(x.duties_of_duty_block) > 0]:
                dbt = next(x for x in self.duty_block_type if db.id in [y.id for y in x.blocks_of_duty_block_type])
                if dbt.other_duties_in_block_allowed == 0:
                    time_start = min(db.duties_of_duty_block, key=lambda duty: duty.time_start).time_start
                    time_end = max(db.duties_of_duty_block, key=lambda duty: duty.time_end).time_end
                    for d in [x for x in self.planning_period.duties_of_planning_period if time_start <= x.time_start <= time_end and x not in db.duties_of_duty_block]:
                        m += duty_assignment[p, d] + duty_block_assignment[p, db] <= 1, "no_other_duties_in_block_{}_{}".format(p, db)

            # no shifts during duty block
            for db in [x for x in self.planning_period.duty_blocks_of_planning_period if len(x.duties_of_duty_block) > 0]:
                dbt = next(x for x in self.duty_block_type if db.id in [y.id for y in x.blocks_of_duty_block_type])
                if dbt.other_team_duties_in_block_allowed == 0:
                    time_start = min(db.duties_of_duty_block, key=lambda duty: duty.time_start).time_start
                    time_end = max(db.duties_of_duty_block, key=lambda duty: duty.time_end).time_end
                    for td in [x for x in self.planning_period.team_duties_of_planning_period if time_start <= x.time_start <= time_end]:
                        m += shift_assignment[p, td] + duty_block_assignment[p, db] <= 1, "no_other_shifts_in_block_{}_{}".format(p, db)

        # No additional duties during duty block of previous planning period
        if previous_planning_period is not None:
            for db in [x for x in previous_planning_period.duty_blocks_of_planning_period if x.other_duties_in_block_allowed == 0 and len(x.duties_of_duty_block) > 0]:
                time_start = min(db.duties_of_duty_block, key=lambda duty: duty.time_start).time_start
                time_end = max(db.duties_of_duty_block, key=lambda duty: duty.time_end).time_end
                if len([x for x in self.list_of_physicians if x.id in [a.user_id for a in self.duty_physician_assignment if a.duty_id == db.duties_of_duty_block[0].id]]) > 0:
                    assigned_physician = [x for x in self.list_of_physicians if x.id in [a.user_id for a in self.duty_physician_assignment if a.duty_id == db.duties_of_duty_block[0].id]][0]
                    for d in [x for x in self.planning_period.duties_of_planning_period if time_start <= x.time_start <= time_end and x not in db.duties_of_duty_block]:
                        # Check if there is a similar duty as d in the last planning period
                        if next((x for x in previous_planning_period.duties_of_planning_period if x.duty_type == d.duty_type and x.time_start.date() == d.time_start.date()), None) is None:
                            m += duty_assignment[assigned_physician, d] == 0, "other_duties_in_block_{}_{}".format(assigned_physician, db)

            # No shifts during duty block of previous planning period
            for tdb in [x for x in previous_planning_period.duty_blocks_of_planning_period if x.other_team_duties_in_block_allowed == 0 and len(x.duties_of_duty_block) > 0]:
                time_start = min(tdb.duties_of_duty_block, key=lambda duty: duty.time_start).time_start
                time_end = max(tdb.duties_of_duty_block, key=lambda duty: duty.time_end).time_end
                assigned_physicians = [x for x in self.list_of_physicians if x.id in [a.user_id for a in self.team_duty_physician_assignment if a.team_duty_id == tdb.duties_of_duty_block[0].id]]
                if len(assigned_physicians) > 0:
                    for td in [x for x in self.planning_period.team_duties_of_planning_period if time_start <= x.time_start <= time_end]:
                        # Check if there is a similar team duty as td in the last planning period
                        if next((x for x in previous_planning_period.team_duties_of_planning_period if x.team_type == td.team_type and x.time_start.date() == td.time_start.date()), None) is None:
                            for p in assigned_physicians:
                                m += shift_assignment[p, td] == 0, "other_shifts_in_block_{}_{}".format(p, tdb)


        # no duties during shift block
        for p in self.list_of_physicians:
            for tdb in [x for x in self.planning_period.team_duty_blocks_of_planning_period if len(x.team_duties_of_team_block) > 0]:
                tbt = next(x for x in self.team_block_types if tdb.id in [y.id for y in x.blocks_of_team_block_type])
                if tbt.other_duties_in_block_allowed == 0:
                    time_start = min(tdb.team_duties_of_team_block, key=lambda team_duty: team_duty.time_start).time_start
                    time_end = max(tdb.team_duties_of_team_block, key=lambda team_duty: team_duty.time_end).time_end
                    for d in [x for x in self.planning_period.duties_of_planning_period if time_start <= x.time_start <= time_end]:
                        m += duty_assignment[p, d] + shift_block_assignment[p, tdb] <= 1, "other_duties_in_shift_block_{}_{}".format(p, tdb)

            # no additional shifts during shift block
            for tdb in [x for x in self.planning_period.team_duty_blocks_of_planning_period if len(x.team_duties_of_team_block) > 0]:
                tbt = next(x for x in self.team_block_types if tdb.id in [y.id for y in x.blocks_of_team_block_type])
                if tbt.other_team_duties_in_block_allowed == 0:
                    time_start = min(tdb.team_duties_of_team_block, key=lambda team_duty: team_duty.time_start).time_start
                    time_end = max(tdb.team_duties_of_team_block, key=lambda team_duty: team_duty.time_end).time_end
                    for td in [x for x in self.planning_period.team_duties_of_planning_period if time_start <= x.time_start <= time_end and x not in tdb.team_duties_of_team_block]:
                        m += shift_assignment[p, td] + shift_block_assignment[p, tdb] <= 1, "other_shift_duties_in_shift_block_{}_{}".format(p, tdb)

        # no duties during shift block of previous planning period
        if previous_planning_period is not None:
            for tdb in [x for x in previous_planning_period.team_duty_blocks_of_planning_period if x.other_duties_in_block_allowed == 0 and len(x.team_duties_of_team_block) > 0]:
                time_start = min(tdb.team_duties_of_team_block, key=lambda team_duty: team_duty.time_start).time_start
                time_end = max(tdb.team_duties_of_team_block, key=lambda team_duty: team_duty.time_end).time_end
                if len([x for x in self.list_of_physicians if x.id in [a.user_id for a in self.team_duty_physician_assignment if a.team_duty_id == tdb.team_duties_of_team_block[0].id]]) > 0:
                    assigned_physician = [x for x in self.list_of_physicians if x.id in [a.user_id for a in self.team_duty_physician_assignment if a.team_duty_id == tdb.team_duties_of_team_block[0].id]][0]
                    for d in [x for x in self.planning_period.duties_of_planning_period if time_start <= x.time_start <= time_end]:
                        # Check if there is a similar duty as d in the last planning period
                        if next((x for x in previous_planning_period.duties_of_planning_period if x.duty_type == d.duty_type and x.time_start.date() == d.time_start.date()), None) is None:
                            m += duty_assignment[assigned_physician, d] == 0, "other_duties_in_shift_block_{}_{}".format(assigned_physician, tdb)

            # no additional shifts during shift block of previous planning period
            for tdb in [x for x in previous_planning_period.team_duty_blocks_of_planning_period if x.other_team_duties_in_block_allowed == 0 and len(x.team_duties_of_team_block) > 0]:
                time_start = min(tdb.team_duties_of_team_block, key=lambda team_duty: team_duty.time_start).time_start
                time_end = max(tdb.team_duties_of_team_block, key=lambda team_duty: team_duty.time_end).time_end
                assigned_physicians = [x for x in self.list_of_physicians if x.id in [a.user_id for a in self.team_duty_physician_assignment if a.team_duty_id == tdb.team_duties_of_team_block[0].id]]
                if len(assigned_physicians) > 0:
                    for td in [x for x in self.planning_period.team_duties_of_planning_period if time_start <= x.time_start <= time_end]:
                        # Check if there is a similar shift as td in the last planning period
                        if next((x for x in previous_planning_period.team_duties_of_planning_period if x.team_type == td.team_type and x.time_start.date() == td.time_start.date()), None) is None:
                            for p in assigned_physicians:
                                m += shift_assignment[p, td] == 0, "other_shifts_in_team_block_{}_{}".format(p, tdb)


    # CONSECUTIVE ASSIGNMENT

        # shift blocks should be assigned to the same physician if desired
        for td_block_type in [x for x in self.team_block_types if x.consecutive_assignment]:
            for bl in [x for x in self.planning_period.team_duty_blocks_of_planning_period if x.team_block_type == td_block_type.id]:
                for p in self.list_of_physicians:
                    m += consecutive_shift_block_assignment[p, bl] - shift_block_assignment[p, bl] <= 0, "shift_block_consec_periods_{}_{}".format(p, bl)

                previous_team_block = next((x for x in self.planning_period.team_duty_blocks_of_planning_period if x.id == bl.previous_team_duty_block), None)

                if previous_team_block is not None:
                    for p in self.list_of_physicians:
                        m += consecutive_shift_block_assignment[p, bl] - shift_block_assignment[p, previous_team_block] <= 0, "team_block_consec_periods_2_{}_{}".format(p, bl)
                else:
                    # find physicians which are assigned to the shift of previous planning period
                    assigned_physicians = []
                    if previous_planning_period is not None:
                        list_of_previous_team_duty_blocks = [x.previous_team_duty_block for x in previous_planning_period.team_duty_blocks_of_planning_period if x.team_block_type == td_block_type.id]
                        previous_team_block = next((x for x in previous_planning_period.team_duty_blocks_of_planning_period if x.team_block_type == td_block_type.id and x.id not in list_of_previous_team_duty_blocks), None)
                        if previous_team_block is not None:
                            team_duty_of_block = previous_team_block.team_duties_of_team_block[0].id
                            assigned_physicians_ids = [x.user_id for x in self.team_duty_physician_assignment if x.team_duty_id == team_duty_of_block and x.planning_period_id == previous_planning_period.id]
                            assigned_physicians = [x for x in self.list_of_physicians if x.id in assigned_physicians_ids]

                    # consecutive_shift_block_assignment can only be positive if the previous shift is assigned to that physician
                    for p in [x for x in self.list_of_physicians if x not in assigned_physicians]:
                        m += consecutive_shift_block_assignment[p, bl] == 0, "consecutive_shift_block_assignment_{}_{}".format(p, bl)

        # maximal number of consecutive shift blocks
        for td_block_type in [x for x in self.team_block_types if x.consecutive_assignment_desired]:
            maximal_consecutive_blocks = td_block_type.maximal_consecutive_blocks
            for bl in [x for x in self.planning_period.team_duty_blocks_of_planning_period if x.team_block_type == td_block_type.id]:
                blocks = [bl]
                for i in range(1, maximal_consecutive_blocks + 1):
                    previous_team_block = next((x for x in self.planning_period.team_duty_blocks_of_planning_period if x.id == blocks[-1].previous_team_duty_block), None)
                    if previous_team_block is not None:
                        blocks.append(previous_team_block)

                if len(blocks) > maximal_consecutive_blocks:
                    for p in self.list_of_physicians:
                        m += mip.xsum(shift_block_assignment[p, b] for b in blocks) - max_cons_shift_violation[bl] <= maximal_consecutive_blocks, "max_consecutive_team_blocks_{}_{}".format(p, bl)

            if previous_planning_period is not None:
                list_of_previous_team_duty_blocks = [x.previous_team_duty_block for x in previous_planning_period.team_duty_blocks_of_planning_period if x.team_block_type == td_block_type.id]
                last_team_block = next((x for x in previous_planning_period.team_duty_blocks_of_planning_period if x.team_block_type == td_block_type.id and x.id not in list_of_previous_team_duty_blocks), None)
                if last_team_block is not None:
                    last_team_duty = last_team_block.team_duties_of_team_block[0].id
                    assigned_physicians_ids = [x.user_id for x in self.team_duty_physician_assignment if x.team_duty_id == last_team_duty and x.planning_period_id == previous_planning_period.id]
                    # assigned physicians to the last shift block of the previous planning period
                    assigned_physicians = [x for x in self.list_of_physicians if x.id in assigned_physicians_ids]

                    for p in assigned_physicians:
                        # for all assigned physicians, check how often they got assigned consecutively to the last shift blocks
                        number_of_tblocks_last_pp = 1
                        counting_block = last_team_block
                        for _ in range(1, maximal_consecutive_blocks + 1):
                            prev_block = next((x for x in previous_planning_period.team_duty_blocks_of_planning_period if x.id == counting_block.previous_team_duty_block), None)
                            if prev_block is not None:
                                td_of_pref_block = prev_block.team_duties_of_team_block[0]
                                td_of_pref_block_assignment = next((x for x in self.team_duty_physician_assignment if x.team_duty_id == td_of_pref_block.id and x.user_id == p.id), None)
                                if td_of_pref_block_assignment is not None:
                                    number_of_tblocks_last_pp += 1

                                    counting_block = prev_block

                                else:
                                    break
                            else:
                                break

                        # restrict the number of consecutive assignments to the shift blocks regarding the previous planning period
                        block = next((x for x in self.planning_period.team_duty_blocks_of_planning_period if x.team_block_type == td_block_type.id and x.previous_team_duty_block is None), None)
                        if block is not None:
                            blocks = [block]
                            for i in range(1, maximal_consecutive_blocks + 1 - number_of_tblocks_last_pp):
                                next_team_block = next((x for x in self.planning_period.team_duty_blocks_of_planning_period if x.previous_team_duty_block == blocks[-1].id), None)
                                if next_team_block is not None:
                                    blocks.append(next_team_block)

                            m += mip.xsum(shift_block_assignment[p, b] for b in blocks) - max_cons_shift_violation[block] <= maximal_consecutive_blocks - number_of_tblocks_last_pp, "max_consecutive_team_blocks_last_pp_{}_{}".format(p, td_block_type.name)

        # duties get assigned to the same physician if desired
        for d in self.planning_period.duties_of_planning_period:
            duty_type = next(x for x in self.duty_types if x.id == d.duty_type)
            if duty_type.consecutive_assignment:
                for p in self.list_of_physicians:
                    m += consecutive_duty_assignment[p, d] - duty_assignment[p, d] <= 0

                previous_duty = next((x for x in self.planning_period.duties_of_planning_period if x.id == d.previous_duty), None)

                if previous_duty:
                    for p in self.list_of_physicians:
                        m += consecutive_duty_assignment[p, d] - duty_assignment[p, previous_duty] <= 0, "duty_consec_periods_{}_{}".format(p, d)
                else:
                    # find physician which is assigned to the last duty of previous planning period
                    if previous_planning_period is not None:
                        previous_duty = next((x for x in previous_planning_period.duties_of_planning_period if x.duty_type == d.duty_type), None)
                        assigned_physician_id = next((x.user_id for x in self.duty_physician_assignment if x.duty_id == previous_duty.id), None)
                        assigned_physician = next((x for x in self.list_of_physicians if x.id == assigned_physician_id), None)
                        if assigned_physician is not None:
                            for p in [x for x in self.list_of_physicians if x != assigned_physician]:
                                m += consecutive_duty_assignment[p, d] == 0, "duty_consec_periods_{}_{}".format(p, d)


    # QUALIFICATIONS

        # only physicians can be assigned to duties which fulfill the required qualifications
        for p in self.list_of_physicians:
            fixed_duty_assignment_ids = [x.duty_id for x in self.duty_physician_assignment if x.user_id == p.id and x.planning_period_id == self.planning_period.id and x.fixed_assignment]
            fixed_duty_assignment_ids += [x.duty_id for x in self.add_duty_assignments if x.user_id == p.id and x.planning_period_id == self.planning_period.id]
            duty_blocks_of_fixed_duty_ids = [x for x in self.duty_blocks if any(y.id in fixed_duty_assignment_ids for y in x.duties_of_duty_block)]
            fixed_duty_assignment_ids += [x.id for d in duty_blocks_of_fixed_duty_ids for x in d.duties_of_duty_block]

            unqualified_duties = [x for x in self.planning_period.duties_of_planning_period
                                  if x.id not in [y.id for y in get_duties_that_user_is_qualified_for(self.session, p.id, self.planning_period.id)] and x.id not in fixed_duty_assignment_ids]
            m += mip.xsum(duty_assignment[p, d] for d in unqualified_duties) == 0, "qualification_of_duty_assignment_{}".format(p)


        # only physicians can be assigned to shifts which fulfill the required qualifications
        for p in self.list_of_physicians:
            fixed_team_duty_assignment_ids = [x.team_duty_id for x in self.team_duty_physician_assignment if x.user_id == p.id and x.planning_period_id == self.planning_period.id and x.fixed_assignment]
            team_duty_blocks_of_fixed_team_duty_ids = [x for x in self.team_duty_blocks if any(y.id in fixed_team_duty_assignment_ids for y in x.team_duties_of_team_block)]
            fixed_team_duty_assignment_ids += [x.id for td in team_duty_blocks_of_fixed_team_duty_ids for x in td.team_duties_of_team_block]
            unqualified_team_duties = [x for x in self.planning_period.team_duties_of_planning_period
                                        if x.id not in [y.id for y in get_team_duties_that_user_is_qualified_for(self.session, p.id, self.planning_period.id)] and x.id not in fixed_team_duty_assignment_ids]
            m += mip.xsum(shift_assignment[p, td] for td in unqualified_team_duties) == 0, "qualification_of_shift_assignment_{}".format(p.last_name)


    # WARDS

        # physicians can only be assigned to shifts of wards which they belong to
        for tdt in self.team_duty_types:
            station = [x for x in self.stations if x.id == tdt.station_id][0]
            physicians = [x for x in self.list_of_physicians if station.id not in [i.station_id for i in x.stations_of_physician]]
            team_duties_of_tdt = [x for x in tdt.team_duties_of_type if x in self.planning_period.team_duties_of_planning_period]
            m += mip.xsum(mip.xsum(shift_assignment[p, td] for p in physicians) for td in team_duties_of_tdt) == 0, "shift_of_ward_assignment_{}".format(tdt)


    # REST TIMES

        # between two duties
        for ddrt in self.duty_duty_resting_time:
            for d1 in [x for x in self.planning_period.duties_of_planning_period if x.duty_type == ddrt.duty_type_id]:
                for d2 in [x for x in self.planning_period.duties_of_planning_period
                           if x.duty_type == ddrt.following_duty_type_id
                              and d1.time_start <= x.time_start < d1.time_end + timedelta(hours=ddrt.resting_time_hard)]:
                    for p in self.list_of_physicians:
                        m += duty_assignment[p, d1] + duty_assignment[p, d2] <= 1, "resting_time_1_{}_{}".format(p, d1)

        # between duty and shift
        for dtdrt in self.duty_team_duty_resting_time:
            for d1 in [x for x in self.planning_period.duties_of_planning_period if x.duty_type == dtdrt.duty_type_id]:
                for d2 in [x for x in self.planning_period.team_duties_of_planning_period
                           if d1.time_start <= x.time_start < d1.time_end + timedelta(hours=dtdrt.resting_time_hard)]:
                    for p in self.list_of_physicians:
                        m += duty_assignment[p, d1] + shift_assignment[p, d2] <= 1, "resting_time_2_{}_{}".format(p, d1)

        # between shift and duty
        for tdrt in self.team_duty_resting_time:
            for d1 in [x for x in self.planning_period.team_duties_of_planning_period if x.team_type == tdrt.team_type_id]:
                for d2 in [x for x in self.planning_period.duties_of_planning_period
                           if d1.time_start <= x.time_start < d1.time_end + timedelta(hours=tdrt.resting_time_hard)]:
                    for p in self.list_of_physicians:
                        m += shift_assignment[p, d1] + duty_assignment[p, d2] <= 1, "resting_time_3_{}_{}".format(p, d1)

        # between two shifts
            for d1 in [x for x in self.planning_period.team_duties_of_planning_period if x.team_type == tdrt.team_type_id]:
                for d2 in [x for x in self.planning_period.team_duties_of_planning_period
                           if d1.time_start <= x.time_start < d1.time_end + timedelta(hours=tdrt.resting_time_hard_team)]:
                    for p in self.list_of_physicians:
                        m += shift_assignment[p, d1] + shift_assignment[p, d2] <= 1, "resting_time_4_{}_{}".format(p, d1)

        # desired rest times
        # between duties
        for duties in duty_duty_desired_rest_time_list:
            for p in self.list_of_physicians:
                m += desired_rest_time_duties[p, duties[0], duties[1]] - duty_assignment[p, duties[0]] <= 0, "soft_resting_time_1_{}_{}".format(p, duties[0])
                m += desired_rest_time_duties[p, duties[0], duties[1]] - duty_assignment[p, duties[1]] <= 0, "soft_resting_time_1_{}_{}".format(p, duties[1])
                m += duty_assignment[p, duties[0]] + duty_assignment[p, duties[1]] - desired_rest_time_duties[p, duties[0], duties[1]] <= 1, "soft_resting_time_1_{}_{}".format(p, duties[0])

        # between duty and shift
        for duties in duty_shift_desired_rest_time_list:
            for p in self.list_of_physicians:
                m += desired_rest_time_duty_shift[p, duties[0], duties[1]] - duty_assignment[p, duties[0]] <= 0, "soft_resting_time_2_{}_{}".format(p, duties[0])
                m += desired_rest_time_duty_shift[p, duties[0], duties[1]] - shift_assignment[p, duties[1]] <= 0, "soft_resting_time_2_{}_{}".format(p, duties[1])
                m += duty_assignment[p, duties[0]] + shift_assignment[p, duties[1]] - desired_rest_time_duty_shift[p, duties[0], duties[1]] <= 1, "soft_resting_time_2_{}_{}".format(p, duties[0])

        # between shift and duty
        for duties in shift_duty_desired_rest_time_list:
            for p in self.list_of_physicians:
                m += desired_rest_time_shift_duty[p, duties[0], duties[1]] - shift_assignment[p, duties[0]] <= 0, "soft_resting_time_3_{}_{}".format(p, duties[0])
                m += desired_rest_time_shift_duty[p, duties[0], duties[1]] - duty_assignment[p, duties[1]] <= 0, "soft_resting_time_3_{}_{}".format(p, duties[1])
                m += shift_assignment[p, duties[0]] + duty_assignment[p, duties[1]] - desired_rest_time_shift_duty[p, duties[0], duties[1]] <= 1, "soft_resting_time_3_{}_{}".format(p, duties[0])

        # between shifts
        for duties in shift_shift_desired_rest_time_list:
            for p in self.list_of_physicians:
                m += desired_rest_time_shifts[p, duties[0], duties[1]] - shift_assignment[p, duties[0]] <= 0, "soft_resting_time_4_{}_{}".format(p, duties[0])
                m += desired_rest_time_shifts[p, duties[0], duties[1]] - shift_assignment[p, duties[1]] <= 0, "soft_resting_time_4_{}_{}".format(p, duties[1])
                m += shift_assignment[p, duties[0]] + shift_assignment[p, duties[1]] - desired_rest_time_shifts[p, duties[0], duties[1]] <= 1, "soft_resting_time_4_{}_{}".format(p, duties[0])


    # WEEKEND

        we_factor = {}
        for month in months_:
            days_in_month = calendar.monthrange(month[1], month[0])[1]
            number_of_saturdays_in_whole_month = sum(1 for day in range(1, days_in_month + 1) if calendar.weekday(month[1], month[0], day) == 5)
            if self.planning_period.date_from.month == month[0] and self.planning_period.date_from.year == month[1]:
                number_of_saturdays = sum(1 for day in range(self.planning_period.date_from.day, days_in_month + 1) if calendar.weekday(month[1], month[0], day) == 5)
                we_factor[month] = number_of_saturdays / number_of_saturdays_in_whole_month
            elif self.planning_period.date_to.month == month[0] and self.planning_period.date_to.year == month[1]:
                number_of_saturdays = sum(1 for day in range(1, self.planning_period.date_to.day + 1) if calendar.weekday(month[1], month[0], day) == 5)
                we_factor[month] = number_of_saturdays / number_of_saturdays_in_whole_month
            else:
                we_factor[month] = 1

        # weekend variables are set
        for p in self.list_of_physicians:
            for w in weekends_:
                for d in duties_of_weekend[w]:
                    m += weekend_attendance[p, w] - duty_assignment[p, d] >= 0, "weekend_attendence_{}_{}".format(p, w)
                for td in team_duties_of_weekend[w]:
                    m += weekend_attendance[p, w] - shift_assignment[p, td] >= 0, "weekend_attendence_{}_{}".format(p, w)
                m += weekend_attendance[p, w] - mip.xsum(shift_assignment[p, td] for td in team_duties_of_weekend[w]) - mip.xsum(duty_assignment[p, d] for d in duties_of_weekend[w]) <= 0, "weekend_attendence_ub_{}_{}".format(p, w)

        # maximal number of consecutive weekends
        if max_consecutive_weekends is not None:
            if max_consecutive_weekends > 0:
                for p in self.list_of_physicians:
                    for i in range(len(weekends_) - max_consecutive_weekends):
                        m += mip.xsum(weekend_attendance[p, w] for w in weekends_[i:i + max_consecutive_weekends + 1]) <= max_consecutive_weekends, "max_consecutive_weekends_{}_{}".format(p, i)

        # maximal number of consecutive weekends considering previous planning period
        weekends_of_last_pp = []
        if len(previous_planning_period_list) > 0:
            previous_planning_period = previous_planning_period_list[0]
            get_weekends(weekends_of_last_pp, previous_planning_period)

            # delete weekend in previous_planning_period if it is in the current planning period
            for w_lp in weekends_of_last_pp:
                for w in weekends_:
                    if (w[0] <= w_lp[0] <= w[1]) or (w[0] <= w_lp[1] <= w[1]):
                        weekends_of_last_pp.remove(w_lp)

            duties_of_weekend_last_pp = {w: [d for d in previous_planning_period.duties_of_planning_period
                                     if d.time_start < w[1] and d.time_end > w[0]]
                                 for w in weekends_of_last_pp}

            team_duties_of_weekend_last_pp = {w: [td for td in previous_planning_period.team_duties_of_planning_period
                                          if td.time_start < w[1] and td.time_end > w[0]]
                                      for w in weekends_of_last_pp}

            attendence_of_last_weekends = {p: int(0) for p in self.list_of_physicians}
            for p in self.list_of_physicians:
                for w in weekends_of_last_pp:
                    if p.id in [x.user_id for x in self.duty_physician_assignment if x.planning_period_id == previous_planning_period.id and x.duty_id in [x.id for x in duties_of_weekend_last_pp[w]]]\
                            or p.id in [x.user_id for x in self.team_duty_physician_assignment if x.planning_period_id == previous_planning_period.id and x.team_duty_id in [x.id for x in team_duties_of_weekend_last_pp[w]]]:
                        attendence_of_last_weekends[p] += 1
                    else:
                        attendence_of_last_weekends[p] = 0

            if max_consecutive_weekends is not None:
                if max_consecutive_weekends > 0:
                    for p in self.list_of_physicians:
                        if max_consecutive_weekends - attendence_of_last_weekends[p] >= 0:
                            m += mip.xsum(weekend_attendance[p, w] for w in weekends_[0: max_consecutive_weekends - attendence_of_last_weekends[p] + 1]) <= max_consecutive_weekends - attendence_of_last_weekends[p], "max_consecutive_weekends_last_pp_{}".format(p)
                        else:
                            m += weekend_attendance[p, weekends_[0]] == 0, "max_consecutive_weekends_last_pp_{}".format(p)

        # weekend preference violation
        for w in weekends_:
            for p in [s for s in self.list_of_physicians if s.id in [x.user_id for x in self.preferences_weekend if x.planning_period_id == self.planning_period.id and x.option == "mehrereDienste"]]:
                m += 2 * weekend_attendance[p, w] - weekend_preference_violation[p, w]\
                    - mip.xsum(shift_assignment[p, td] for td in team_duties_of_weekend[w])\
                    - mip.xsum(duty_assignment[p, d] for d in duties_of_weekend[w])\
                    <= 0, "weekend_violation_{}_{}".format(p, w)

            for p in [s for s in self.list_of_physicians if s.id in [x.user_id for x in self.preferences_weekend if x.planning_period_id == self.planning_period.id and x.option == "einDienst"]]:
                m += weekend_attendance[p, w] + weekend_preference_violation[p, w]\
                    - mip.xsum(shift_assignment[p, td] for td in team_duties_of_weekend[w])\
                    - mip.xsum(duty_assignment[p, d] for d in duties_of_weekend[w]) >= 0, "weekend_violation_2_{}_{}".format(p, w)

        # maximal number of weekends per month
        if max_number_weekends_per_month < 5 and min_free_weekends_per_month_soft is False:
            for p in self.list_of_physicians:
                for month in months_:
                    m += mip.xsum(weekend_attendance[p, weekend] for weekend in weekends_of_month[month]) <= round(we_factor[month] * max_number_weekends_per_month), "Max_Number_Weekends_Per_Month({},{})".format(p, month)

        # desired maximal number of weekends per month
        if max_number_weekends_per_month < 5 and min_free_weekends_per_month_soft is True:
            for p in self.list_of_physicians:
                for month in months_:
                    m += mip.xsum(weekend_attendance[p, weekend] for weekend in weekends_of_month[month]) - max_weekend_violation[p, month] <= round(we_factor[month] * max_number_weekends_per_month), "Max_Number_Weekends_Per_Month_soft({},{})".format(p, month)

        # minimal number of free weekends per month
        if max_number_weekends_per_month < 5 and min_free_weekends_per_month_soft is False:
            for p in self.list_of_physicians:
                for month in months_:
                    m += mip.xsum(weekend_attendance[p, weekend] for weekend in weekends_of_month[month]) <= len(weekends_of_month[month]) - round(we_factor[month] * min_free_weekends_per_month), "Min_Free_Weekends_Per_Month({},{})".format(p, month)

        # desired minimal number of free weekends per month
        if max_number_weekends_per_month < 5 and min_free_weekends_per_month_soft is True:
            for p in self.list_of_physicians:
                for month in months_:
                    m += mip.xsum(weekend_attendance[p, weekend] for weekend in weekends_of_month[month]) - min_free_weekend_violation[p, month] <= len(weekends_of_month[month]) - round(we_factor[month] * min_free_weekends_per_month), "Min_Free_Weekends_Per_Month_soft({},{})".format(p, month)


    # POOLS

        bundesland = self.session.query(ApplicationSettings).first().bundesland
        holiday = holidays.country_holidays('DE', subdiv=bundesland)
        duties_of_pool = {pool: [] for pool in self.pools}
        duties_of_pool_previous_pp = {pool: [] for pool in self.pools}
        physicians_of_pool = {pool: [x for x in self.list_of_physicians if x.id in [a.physician_id for a in pool.physicians_that_have_pool
                                                                     if a.date_from <= self.planning_period.date_from and a.date_to >= self.planning_period.date_to] and x.planned_manually == 0] for pool in self.pools}
        for pool in self.pools:
            duties_in_this_pool_previous_pp = None
            dt_id_list = [x.duty_type_id for x in pool.duty_type_of_pool if x.holidays is False]
            duties_in_this_pool = [x for x in self.planning_period.duties_of_planning_period if
                                   x.duty_type in dt_id_list and x.time_start.date() not in holiday]
            if previous_planning_period is not None:
                duties_in_this_pool_previous_pp = [x for x in previous_planning_period.duties_of_planning_period if
                                                   x.duty_type in dt_id_list and x.time_start.date() not in holiday]

            dt_id_list = [x.duty_type_id for x in pool.duty_type_of_pool if x.holidays is True]
            duties_in_this_pool += [x for x in self.planning_period.duties_of_planning_period if
                                   x.duty_type in dt_id_list and x.time_start.date() in holiday]
            if previous_planning_period is not None:
                duties_in_this_pool_previous_pp += [x for x in previous_planning_period.duties_of_planning_period if
                                                   x.duty_type in dt_id_list and x.time_start.date() in holiday]
            duties_of_pool[pool] = duties_in_this_pool
            if previous_planning_period is not None:
                duties_of_pool_previous_pp[pool] = duties_in_this_pool_previous_pp

        exact_number_of_duties_per_physician_and_pool = {(p, pool): 0
                                                         for pool in [x for x in self.pools if x.exact_number_of_duties_per_month is not None]
                                                         for p in [x for x in self.list_of_physicians if x.id in [a.physician_id for a in pool.physicians_that_have_pool
                                                                                                                  if a.date_from <= self.planning_period.date_from and a.date_to >= self.planning_period.date_to]]}

        # exact number of duties in pool
        for pool in [x for x in self.pools if x.exact_number_of_duties_per_month is not None]:
            for p in physicians_of_pool[pool]:
                m += mip.xsum(duty_assignment[p, d] for d in duties_of_pool[pool]) == round(pool.exact_number_of_duties_per_month), "Exact_Number_Of_Duties({},{})".format(pool, p)

        # upper bound on number of duties in pool
        for pool in [x for x in self.pools if x.maximal_number_of_duties is not None and x.maximal_number_of_duties_soft is False]:
            for p in physicians_of_pool[pool]:
                m += mip.xsum(duty_assignment[p, d] for d in self.planning_period.duties_of_planning_period if d in duties_of_pool[pool] and d.time_start.date() >= self.planning_period.date_from) <= pool.maximal_number_of_duties, "Maximal_Number_Of_Duties({},{})".format(pool, p)

        # desired upper bound on number of duties in pool
        for pool in [x for x in self.pools if x.maximal_number_of_duties_soft is True and x.maximal_number_of_duties is not None]:
            for p in physicians_of_pool[pool]:
                big_M = max(sum(1 for d in self.planning_period.duties_of_planning_period if d in duties_of_pool[pool]), pool.maximal_number_of_duties)
                m += mip.xsum(duty_assignment[p, d] for d in self.planning_period.duties_of_planning_period if d in duties_of_pool[pool]) - max_number_of_duties_violation[pool, p] <= pool.maximal_number_of_duties, "Maximal_Number_Of_Duties_Soft({},{})".format(pool, p)

        # lower bound on number of duties in pool
        for pool in [x for x in self.pools if x.minimal_number_of_duties is not None and x.minimal_number_of_duties_soft is False]:
            for p in physicians_of_pool[pool]:
                m += mip.xsum(duty_assignment[p, d] for d in self.planning_period.duties_of_planning_period if d in duties_of_pool[pool] and d.time_start.date() >= self.planning_period.date_from) >= pool.minimal_number_of_duties, "Minimal_Number_Of_Duties({},{})".format(pool, p)

        # desired lower bound on number of duties in pool
        for pool in [x for x in self.pools if x.minimal_number_of_duties_soft is True and x.minimal_number_of_duties is not None]:
            for p in physicians_of_pool[pool]:
                big_M = max(sum(1 for d in self.planning_period.duties_of_planning_period if d in duties_of_pool[pool]), pool.minimal_number_of_duties)
                m += mip.xsum(duty_assignment[p, d] for d in self.planning_period.duties_of_planning_period if d in duties_of_pool[pool]) + min_number_of_duties_violation[pool, p] >= pool.minimal_number_of_duties, "Minimal_Number_Of_Duties_Soft({},{})".format(pool, p)

        # maximal number of physicians that can do a duty on the same day
        for pool in [x for x in self.pools if x.maximal_number_of_physicians is True]:
            for i in range((self.planning_period.date_to - self.planning_period.date_from).days + 1):
                m += mip.xsum(duty_assignment[p, d] for p in physicians_of_pool[pool] for d in duties_of_pool[pool] if d.time_start.date() == (self.planning_period.date_from + timedelta(days=i))) <= pool.maximal_number_of_physicians, "Maximal_Number_Of_Physicians({},{})".format(pool, i)

        # desired maximal number of physicians that can do a duty on the same day
        for pool in [x for x in self.pools if x.maximal_number_of_physicians_soft is True]:
            for day in range((self.planning_period.date_to - self.planning_period.date_from).days + 1):
                m += mip.xsum(duty_assignment[p, d] for p in physicians_of_pool[pool] for d in duties_of_pool[pool] if d.time_start.date() == (self.planning_period.date_from + timedelta(days=day))) - max_number_of_physicians_violation[pool, day] <= pool.maximal_number_of_physicians, "Maximal_Number_Of_Physicians({},{})".format(pool, day)

        # fair distribution in the pools
        pool_physician_print = {(pool, p): [] for pool in self.pools for p in physicians_of_pool[pool]}
        pool_print = {pool: [] for pool in self.pools}

        # Manually planned duties of manually planned physicians are excluded in the fair distribution
        manually_planned_physicians = [x.id for x in self.list_of_physicians if x.planned_manually == 1]
        manually_planned_duties_id = [x.duty_id for x in self.session.query(DutyPhysicianAssignment).all() if
                                      x.planning_period_id == self.planning_period.id and x.fixed_assignment == 1 and x.user_id in manually_planned_physicians]

        for pool in [x for x in self.pools if x.fair_distribution]:
            # remove physicians from pool with exact number of duties
            for pool_ex in [x for x in self.pools if x.exact_number_of_duties_per_month is not None]:
                if set(duties_of_pool[pool]) == set(duties_of_pool[pool_ex]):
                    for p in [x for x in physicians_of_pool[pool_ex] if x in physicians_of_pool[pool]]:
                        physicians_of_pool[pool].remove(p)

            duties_of_pool_2b_planned = [x for x in duties_of_pool[pool] if x.id not in manually_planned_duties_id]
            pool_print[pool].append("Pool: " + pool.name)

            if len(duties_of_pool_2b_planned) == 0:
                pool_print[pool].append("Keine Dienste in diesem Pool")
                print("Keine Dienste in diesem Pool: {}".format(pool.name))
                continue

            number_attendance_phy = {phy: 0 for phy in physicians_of_pool[pool]}
            for phy in physicians_of_pool[pool]:

                # calculating absent duties of physician
                absent_duties_of_physician = [x for x in duties_of_pool_2b_planned if x in duty_absences_of_physician[phy]]
                absent_days_of_physician = [x.day for x in self.session.query(AbsencePhysicians).filter(AbsencePhysicians.user_id == phy.id).all()]
                for day in absent_days_of_physician:
                    for duty in [x for x in duties_of_pool_2b_planned if x.time_start.date() == day]:
                        absent_duties_of_physician.append(duty)

                    for duty_type_id in [x.duty_type_id for x in pool.duty_type_of_pool]:
                        duties_of_duty_type_in_pool = [x for x in duties_of_pool_2b_planned if x.duty_type == duty_type_id]
                        duty_type = next(x for x in self.duty_types if x.id == duty_type_id)
                        if duty_type.before_absence is False:
                            for d in [x for x in duties_of_duty_type_in_pool if x.time_start.date() == (day - timedelta(days=1))]:
                                absent_duties_of_physician.append(d)

                        if duty_type.after_absence is False:
                            for d in [x for x in duties_of_duty_type_in_pool if x.time_start.date() == (day + timedelta(days=1))]:
                                absent_duties_of_physician.append(d)

                # duties of physician while he is not absent
                duties_of_physician = [x for x in duties_of_pool_2b_planned if x not in absent_duties_of_physician]
                number_attendance_phy[phy] = len(duties_of_physician)

            flexible_number_of_duties_in_pool = len(duties_of_pool_2b_planned)

            pyhsicians_with_fixed_number = []
            # Consider if exact number of duties is set in this pool
            for pool_ex in [x for x in self.pools if x.exact_number_of_duties_per_month is not None]:
                if set(duties_of_pool[pool]) == set(duties_of_pool[pool_ex]):
                    pyhsicians_with_fixed_number.append([x for x in physicians_of_pool[pool_ex]])
                    for p in physicians_of_pool[pool_ex]:
                        flexible_number_of_duties_in_pool -= exact_number_of_duties_per_physician_and_pool[p, pool_ex]

            # sum of number of duties in this pool, that physician phy can attend times the workload of physician phy over all physicians
            whole_workload = sum([float(phy.beschaeftigungsumfang) * number_attendance_phy[phy] for phy in physicians_of_pool[pool]])

            pool_print[pool].append("Dienste in Pool: " + str(flexible_number_of_duties_in_pool))
            pool_print[pool].append("Anzahl an Ärzten in Pool: " + str(len(physicians_of_pool[pool])))
            pool_print[pool].append("Summe der Sollzahlen: " + str(sum(flexible_number_of_duties_in_pool * float(phy.beschaeftigungsumfang) * float(number_attendance_phy[phy]/whole_workload) for phy in physicians_of_pool[pool])))

            for phy in [x for x in physicians_of_pool[pool] if x not in pyhsicians_with_fixed_number]:
                pool_physician_print[pool, phy].append("Arzt: " + phy.last_name + " ist bei " + str(number_attendance_phy[phy]) + " Diensten anwesend")
                pool_physician_print[pool, phy].append("Arzt: " + phy.last_name + " hat Beschäftigungsumfang " + str(float(phy.beschaeftigungsumfang)))
                pool_physician_print[pool, phy].append("Arzt: " + phy.last_name + " Sollzahl: " + str(flexible_number_of_duties_in_pool * float(phy.beschaeftigungsumfang) * float(number_attendance_phy[phy]/whole_workload)))
                m += mip.xsum(duty_assignment[phy, d] for d in duties_of_pool[pool]) + deviation_duties_pool_neg[pool, phy] >= math.floor(flexible_number_of_duties_in_pool * float(phy.beschaeftigungsumfang) * float(number_attendance_phy[phy]/whole_workload)), "Fair_Distribution_Neg({},{})".format(pool, phy)
                m += mip.xsum(duty_assignment[phy, d] for d in duties_of_pool[pool]) - deviation_duties_pool_pos[pool, phy] <= math.ceil(flexible_number_of_duties_in_pool * float(phy.beschaeftigungsumfang) * float(number_attendance_phy[phy]/whole_workload)), "Fair_Distribution_Pos({},{})".format(pool, phy)


    # PREVIOUS PLANNING PERIOD

        soft_duty_resting_time_last_period = {}
        soft_team_duty_resting_time_last_period = {}

        # rest times after duties of previous planning period
        previous_planning_period = [x for x in self.all_planning_periods if x.id == self.planning_period.previous_planning_period_id]
        if len(previous_planning_period) > 0:
            additional_duty_assignments_last_pp = self.session.query(DutyAdditionalPhysicianAssignment).filter_by(planning_period_id=previous_planning_period[0].id).all()
            for p in self.list_of_physicians:
                for duty_type in self.duty_types:
                    if len([x for x in previous_planning_period[0].duties_of_planning_period if x.duty_type == duty_type.id and len([s for s in self.duty_physician_assignment if s.duty_id == x.id and s.user_id == p.id] + [s for s in additional_duty_assignments_last_pp if s.duty_id == x.id and s.user_id == p.id]) > 0]) > 0:
                        last_duty_of_previous_pp = max([x for x in previous_planning_period[0].duties_of_planning_period if x.duty_type == duty_type.id and len([s for s in self.duty_physician_assignment if s.duty_id == x.id and s.user_id == p.id] + [s for s in additional_duty_assignments_last_pp if s.duty_id == x.id and s.user_id == p.id]) > 0], key=lambda duty: duty.time_end)
                        if last_duty_of_previous_pp is not None:
                            dtdrt = next((x for x in self.duty_team_duty_resting_time if x.duty_type_id == duty_type.id), None)
                            resting_time_hard = dtdrt.resting_time_hard if dtdrt is not None else 0
                            for td in [x for x in self.planning_period.team_duties_of_planning_period if x.time_start < last_duty_of_previous_pp.time_end + timedelta(hours=resting_time_hard)]:
                                m += shift_assignment[p, td] == 0, "resting_time_ppp_1_{}_{}".format(p, td)

                                resting_time_desired = dtdrt.resting_time_desired if dtdrt is not None else 0

                                for td in [x for x in self.planning_period.team_duties_of_planning_period if x.time_start < last_duty_of_previous_pp.time_end + timedelta(hours=resting_time_desired)]:
                                    soft_team_duty_resting_time_last_period[(p, td)] = dtdrt.weight_resting_time

                            for ddrt in [x for x in self.duty_duty_resting_time if x.duty_type_id == duty_type.id]:
                                resting_time_hard = ddrt.resting_time_hard if ddrt is not None else 0
                                for d in [x for x in self.planning_period.duties_of_planning_period if x.duty_type == ddrt.following_duty_type_id and x.time_start < last_duty_of_previous_pp.time_end + timedelta(hours=resting_time_hard)]:
                                    m += duty_assignment[p, d] == 0, "resting_time_2_ppp_{}_{}".format(p, d)

                                resting_time_desired = ddrt.resting_time_desired if ddrt is not None else 0
                                for d in [x for x in self.planning_period.duties_of_planning_period if x.duty_type == ddrt.following_duty_type_id and x.time_start < last_duty_of_previous_pp.time_end + timedelta(hours=resting_time_desired)]:
                                    soft_duty_resting_time_last_period[(p, d)] = ddrt.weight_resting_time

                    for old_duty in [x for x in previous_planning_period[0].duties_of_planning_period if x.duty_type == duty_type.id and x.time_start.date() >= self.planning_period.date_from and len([s for s in self.duty_physician_assignment if s.duty_id == x.id and s.user_id == p.id]) > 0]:
                        # check if duty exists in current planning period
                        if len([x for x in self.planning_period.duties_of_planning_period if x.duty_type == old_duty.duty_type and x.time_start == old_duty.time_start and x.time_end == old_duty.time_end and x.name == old_duty.name]) == 0:
                            dtdrt = next((x for x in self.duty_team_duty_resting_time if x.duty_type_id == duty_type.id), None)
                            resting_time_hard = dtdrt.resting_time_hard if dtdrt is not None else 0
                            for td in [x for x in self.planning_period.team_duties_of_planning_period if old_duty.time_start <= x.time_start < old_duty.time_end + timedelta(hours=resting_time_hard)]:
                                m += shift_assignment[p, td] == 0, "resting_time_ppp_2_{}_{}".format(p, td)

                                resting_time_desired = dtdrt.resting_time_desired if dtdrt is not None else 0
                                for td in [x for x in self.planning_period.team_duties_of_planning_period if old_duty.time_start <= x.time_start < old_duty.time_end + timedelta(hours=resting_time_desired)]:
                                    soft_team_duty_resting_time_last_period[(p, td)] = dtdrt.weight_resting_time

                            for ddrt in [x for x in self.duty_duty_resting_time if x.duty_type_id == duty_type.id]:
                                resting_time_hard = ddrt.resting_time_hard if ddrt is not None else 0
                                for d in [x for x in self.planning_period.duties_of_planning_period if x.duty_type == ddrt.following_duty_type_id and old_duty.time_start <= x.time_start < old_duty.time_end + timedelta(hours=resting_time_hard)]:
                                    m += duty_assignment[p, d] == 0, "resting_time_2_ppp_{}_{}".format(p, d)

                                resting_time_desired = ddrt.resting_time_desired if ddrt is not None else 0
                                for d in [x for x in self.planning_period.duties_of_planning_period if x.duty_type == ddrt.following_duty_type_id and old_duty.time_start <= x.time_start < old_duty.time_end + timedelta(hours=resting_time_desired)]:
                                    soft_duty_resting_time_last_period[(p, d)] = ddrt.weight_resting_time

                # rest times after shifts of previous planning period
                for team_duty_type in self.team_duty_types:
                    if len([x for x in previous_planning_period[0].team_duties_of_planning_period if x.team_type == team_duty_type.id and x.time_start.date() < self.planning_period.date_from and len([s for s in self.team_duty_physician_assignment if s.team_duty_id == x.id and s.user_id == p.id]) > 0]) > 0:
                        last_team_duty_of_previous_pp = max([x for x in previous_planning_period[0].team_duties_of_planning_period if x.team_type == team_duty_type.id and x.time_start.date() < self.planning_period.date_from and len([s for s in self.team_duty_physician_assignment if s.team_duty_id == x.id and s.user_id == p.id]) > 0], key=lambda team_duty: team_duty.time_end)
                        if last_team_duty_of_previous_pp is not None:
                            tdrt = next((x for x in self.team_duty_resting_time if x.team_type_id == team_duty_type.id), None)
                            resting_time_hard = tdrt.resting_time_hard if tdrt is not None else 0
                            for d in [x for x in self.planning_period.duties_of_planning_period if last_team_duty_of_previous_pp.time_start <= x.time_start < last_team_duty_of_previous_pp.time_end + timedelta(hours=resting_time_hard)]:
                                m += duty_assignment[p, d] == 0, "resting_time_ppp_3_{}_{}".format(p, d)

                                resting_time_desired = tdrt.resting_time_desired if tdrt is not None else 0
                                for d in [x for x in self.planning_period.duties_of_planning_period if last_team_duty_of_previous_pp.time_start <= x.time_start < last_team_duty_of_previous_pp.time_end + timedelta(hours=resting_time_desired)]:
                                    soft_duty_resting_time_last_period[(p, d)] = tdrt.weight_resting_time

                                resting_time_hard_team = tdrt.resting_time_hard_team if tdrt is not None else 0
                                for td in [x for x in self.planning_period.team_duties_of_planning_period if last_team_duty_of_previous_pp.time_start <= x.time_start < last_team_duty_of_previous_pp.time_end + timedelta(hours=resting_time_hard_team)]:
                                    m += shift_assignment[p, td] == 0, "resting_time_ppp_4_{}_{}".format(p, td)

                                resting_time_desired_team = tdrt.resting_time_desired_team if tdrt is not None else 0
                                for td in [x for x in self.planning_period.team_duties_of_planning_period if last_team_duty_of_previous_pp.time_start <= x.time_start < last_team_duty_of_previous_pp.time_end + timedelta(hours=resting_time_desired_team)]:
                                    soft_team_duty_resting_time_last_period[(p, td)] = tdrt.weight_resting_time

                    for old_team_duty in [x for x in previous_planning_period[0].team_duties_of_planning_period if x.team_type == team_duty_type.id and x.time_start.date() >= self.planning_period.date_from and len([s for s in self.team_duty_physician_assignment if s.team_duty_id == x.id and s.user_id == p.id]) > 0]:
                        # check if team duty exists in current planning period
                        if len([x for x in self.planning_period.team_duties_of_planning_period if x.team_type == old_team_duty.team_type and x.time_start == old_team_duty.time_start and x.time_end == old_team_duty.time_end and x.name == old_team_duty.name]) == 0:
                            tdrt = next((x for x in self.team_duty_resting_time if x.team_type_id == team_duty_type.id), None)
                            resting_time_hard = tdrt.resting_time_hard if tdrt is not None else 0
                            for d in [x for x in self.planning_period.duties_of_planning_period if old_team_duty.time_start <= x.time_start < old_team_duty.time_end + timedelta(hours=resting_time_hard)]:
                                m += duty_assignment[p, d] == 0, "resting_time_ppp_5_{}_{}".format(p, d)

                                resting_time_desired = tdrt.resting_time_desired if tdrt is not None else 0
                                for d in [x for x in self.planning_period.duties_of_planning_period if old_team_duty.time_start <= x.time_start < old_team_duty.time_end + timedelta(hours=resting_time_desired)]:
                                    soft_duty_resting_time_last_period[(p, d)] = tdrt.weight_resting_time

                                resting_time_hard_team = tdrt.resting_time_hard_team if tdrt is not None else 0
                                for td in [x for x in self.planning_period.team_duties_of_planning_period if old_team_duty.time_start <= x.time_start < old_team_duty.time_end + timedelta(hours=resting_time_hard_team)]:
                                    m += shift_assignment[p, td] == 0, "resting_time_ppp_6_{}_{}".format(p, td)

                                resting_time_desired_team = tdrt.resting_time_desired_team if tdrt is not None else 0
                                for td in [x for x in self.planning_period.team_duties_of_planning_period if old_team_duty.time_start <= x.time_start < old_team_duty.time_end + timedelta(hours=resting_time_desired_team)]:
                                    soft_team_duty_resting_time_last_period[(p, td)] = tdrt.weight_resting_time

        # free days after shift blocks of previous planning period
        previous_planning_period = [x for x in self.all_planning_periods if x.id == self.planning_period.previous_planning_period_id]
        if len(previous_planning_period) > 0:
            for p in self.list_of_physicians:
                for td_block_type in self.team_block_types:
                    if len([x for x in previous_planning_period[0].team_duty_blocks_of_planning_period if x.team_block_type == td_block_type.id]) > 0:
                        td_blocks_of_last_pp = [x for x in previous_planning_period[0].team_duty_blocks_of_planning_period if x.team_block_type == td_block_type.id]
                        td_blocks_of_last_pp_of_physician_p = [x for x in td_blocks_of_last_pp if len([s for s in self.team_duty_physician_assignment if s.team_duty_id == x.team_duties_of_team_block[-1] and s.user_id == p.id]) > 0]
                        if len(td_blocks_of_last_pp_of_physician_p) > 0:
                            last_td_block_of_last_pp_of_physician_p = max(td_blocks_of_last_pp_of_physician_p, key=lambda td_block: td_block.time_end)
                            last_free_day = last_td_block_of_last_pp_of_physician_p.time_end + timedelta(days=td_block_type.free_days_after_block)
                            for td in [x for x in self.planning_period.team_duties_of_planning_period if x.time_start < last_free_day]:
                                m += shift_assignment[p, td] == 0, "resting_time_ppp_7_{}_{}".format(p, td)

                            for d in [x for x in self.planning_period.duties_of_planning_period if x.time_start < last_free_day]:
                                m += duty_assignment[p, d] == 0, "resting_time_ppp_8_{}_{}".format(p, d)

        # free days after duty blocks of previous planning period
                for duty_block_type in self.duty_block_type:
                    if len([x for x in previous_planning_period[0].duty_blocks_of_planning_period if x.type_of_duty_block == duty_block_type.id]) > 0:
                        duty_blocks_of_last_pp = [x for x in previous_planning_period[0].duty_blocks_of_planning_period if x.type_of_duty_block == duty_block_type.id]
                        duty_blocks_of_last_pp_of_physician_p = [x for x in duty_blocks_of_last_pp if len(x.duties_of_duty_block) > 0 and len([s for s in self.duty_physician_assignment if s.duty_id == x.duties_of_duty_block[-1] and s.user_id == p.id]) > 0]
                        if len(duty_blocks_of_last_pp_of_physician_p) > 0:
                            last_duty_block_of_last_pp_of_physician_p = max(duty_blocks_of_last_pp_of_physician_p, key=lambda duty_block: duty_block.time_end)
                            last_free_day = last_duty_block_of_last_pp_of_physician_p.time_end + timedelta(days=duty_block_type.free_days_after_block)
                            for td in [x for x in self.planning_period.team_duties_of_planning_period if x.time_start < last_free_day]:
                                m += shift_assignment[p, td] == 0, "resting_time_ppp_9_{}_{}".format(p, td)

                            for d in [x for x in self.planning_period.duties_of_planning_period if x.time_start < last_free_day]:
                                m += duty_assignment[p, d] == 0, "resting_time_ppp_10_{}_{}".format(p, d)


        # OBJECTIVE

        objective = mip.LinExpr()

        # maximal number of consecutive shift blocks
        for bl in self.planning_period.team_duty_blocks_of_planning_period:
            td_block_type = [x for x in self.team_block_types if x.id == bl.team_block_type][0]
            if td_block_type.consecutive_assignment_desired and td_block_type.maximal_consecutive_blocks_weight is not None:
                objective -= max_cons_shift_violation[bl] * td_block_type.maximal_consecutive_blocks_weight

        # non-mandatory duties should be assigned
        for d in self.planning_period.duties_of_planning_period:
            duty_type = [x for x in self.duty_types if x.id == d.duty_type][0]
            if duty_type.weight_not_mandatory is not None and not duty_type.mandatory:
                objective += duty_type.weight_not_mandatory * mip.xsum(duty_assignment[p, d] for p in self.list_of_physicians)

        # desired assignment of shifts
        for td in self.planning_period.team_duties_of_planning_period:
            team_type = [x for x in self.team_duty_types if x.id == td.team_type][0]
            objective += team_type.weight_of_occupation * desired_shift_assignment[td]
            objective += team_type.weight_of_occupation_2 * max_shift_assignment[td]

        # consecutive assignment of shift blocks
        for p in self.list_of_physicians:
            for bl in [bl for td_block_type in [x for x in self.team_block_types if x.consecutive_assignment]
                        for bl in self.planning_period.team_duty_blocks_of_planning_period
                        if bl.team_block_type == td_block_type.id]:
                tbt = next(x for x in self.team_block_types if x.id == bl.team_block_type)
                objective += tbt.weight_consecutive_assignment * consecutive_shift_block_assignment[p, bl]

        # consecutive assignment of duties
            for d in self.planning_period.duties_of_planning_period:
                for dt in [x for x in self.duty_types if x.consecutive_assignment]:
                    if d in dt.duties_of_type:
                        objective += dt.weight_consecutive_assignment * consecutive_duty_assignment[p, d]

        # desired qualification of duties
                if d.id in [y.id for y in get_duties_that_user_is_qualified_for(self.session, p.id, self.planning_period.id)] and d.id not in [y.id for y in get_duties_that_user_is_qualified_for_and_appropriate(self.session, p.id, self.planning_period.id)]:
                    factor = get_unsuitability(self.session, p.id, d.id)
                    objective += -factor * duty_assignment[p, d]

        # desired qualification of shifts
            for td in self.planning_period.team_duties_of_planning_period:
                if td.id in [y.id for y in get_team_duties_that_user_is_qualified_for(self.session, p.id, self.planning_period.id)] and td.id not in [y.id for y in get_team_duties_that_user_is_qualified_for_and_appropriate(self.session, p.id, self.planning_period.id)]:
                    factor = get_unsuitability_team_duty(self.session, p.id, td.id)
                    objective += -factor * shift_assignment[p, td]

        # desired rest times
        # between duties
        objective -= mip.xsum(mip.xsum(duties[2] * desired_rest_time_duties[p, duties[0], duties[1]] for p in self.list_of_physicians) for duties in duty_duty_desired_rest_time_list)

        # between duty and shift
        objective -= mip.xsum(mip.xsum(duties[2] * desired_rest_time_duty_shift[p, duties[0], duties[1]] for p in self.list_of_physicians) for duties in duty_shift_desired_rest_time_list)

        # between shift and duty
        objective -= mip.xsum(mip.xsum(duties[2] * desired_rest_time_shift_duty[p, duties[0], duties[1]] for p in self.list_of_physicians) for duties in shift_duty_desired_rest_time_list)

        # between shifts
        objective -= mip.xsum(mip.xsum(team_duties[2] * desired_rest_time_shifts[p, team_duties[0], team_duties[1]] for p in self.list_of_physicians) for team_duties in shift_shift_desired_rest_time_list)

        # desired rest times after previous planning period
        # of duties
        objective -= mip.xsum(soft_duty_resting_time_last_period[key] * duty_assignment[key[0], key[1]] for key in soft_duty_resting_time_last_period.keys())

        # of shifts
        objective -= mip.xsum(soft_team_duty_resting_time_last_period[key] * shift_assignment[key[0], key[1]] for key in soft_team_duty_resting_time_last_period.keys())

        # weekend preference violation
        objective -= mip.xsum(mip.xsum(self.general_preferences_configuration.two_days_on_weekend_preference_value * weekend_preference_violation[p, w] for w in weekends_) for p in self.list_of_physicians)

        # desired maximal number of working weekends
        if max_number_weekends_per_month < 5 and min_free_weekends_per_month_soft is True:
            objective -= mip.xsum(mip.xsum(self.weekend.max_number_weekends_per_month_weight * max_weekend_violation[p, month] for month in months_) for p in self.list_of_physicians)

        # desired minimal number of free weekends
        if max_number_weekends_per_month < 5 and min_free_weekends_per_month_soft is True:
            objective -= mip.xsum(mip.xsum(self.weekend.min_free_weekends_per_month_weight * min_free_weekend_violation[p, month] for month in months_) for p in self.list_of_physicians)

        # maximal number of duties in pool
        objective -= mip.xsum(mip.xsum(pool.weight_maximal_number_of_duties * max_number_of_duties_violation[pool, p]
                                         for p in [x for x in self.list_of_physicians if x.id in [a.physician_id for a in pool.physicians_that_have_pool if a.date_from <= self.planning_period.date_from and a.date_to >= self.planning_period.date_to]])
                                for pool in [x for x in self.pools if x.maximal_number_of_duties_soft is True])

        # minimal number of duties in pool
        objective -= mip.xsum(mip.xsum(pool.weight_minimal_number_of_duties * min_number_of_duties_violation[pool, p]
                                       for p in [x for x in self.list_of_physicians if x.id in [a.physician_id for a in pool.physicians_that_have_pool if a.date_from <= self.planning_period.date_from and a.date_to >= self.planning_period.date_to]])
                              for pool in [x for x in self.pools if x.minimal_number_of_duties_soft is True])

        # maximal number of physicians in pool per day
        objective -= mip.xsum(mip.xsum(pool.weight_maximal_number_of_physicians * max_number_of_physicians_violation[pool, day]
                                                  for day in range((self.planning_period.date_to - self.planning_period.date_from).days + 1))
                                for pool in [x for x in self.pools if x.maximal_number_of_physicians_soft is True])

        # preferences of duties
        objective += mip.xsum(mip.xsum([x.default_value for x in self.preference_weights if preference_option.name == x.name][0] * duty_assignment[[x for x in self.list_of_physicians if x.id == dpp.user_id][0],
                                                                 [x for x in self.planning_period.duties_of_planning_period if x.id == dpp.duty_id][0]]
                                         for dpp in [x for x in self.planning_period.duty_preferences_of_planning_period if x.preference == preference_option.id])
                                for preference_option in self.planning_period.planning_period_specific_day_options_preferences_configuration)


        # preferences of shifts
        objective += mip.xsum(mip.xsum(preference_option.value * shift_assignment[[x for x in self.list_of_physicians if x.id == dpp.user_id][0],
                                                                 [x for x in self.planning_period.team_duties_of_planning_period if x.id == dpp.duty_id][0]]
                                         for dpp in [x for x in self.planning_period.team_duty_preferences_of_planning_period if x.preference == preference_option.id])
                                for preference_option in self.planning_period.planning_period_specific_day_options_preferences_configuration)

        # weekly preferences
        weekly_duty_wishes = self.session.query(WeeklyWishesOfPhysiciansPerDuty).filter_by(planning_period_id=self.planning_period.id, is_duty=True).all()
        weekly_team_duty_wishes = self.session.query(WeeklyWishesOfPhysiciansPerDuty).filter_by(planning_period_id=self.planning_period.id, is_team_duty=True).all()

        # of duties
        for wish in weekly_duty_wishes:
            if len([x for x in self.planning_period.duties_of_planning_period if x.id == wish.duty_team_duty_id]) > 0:
                objective += self.session.query(WeeklyBlockSpecificPreferences).filter_by(id=wish.weekly_block_specific_preference).all()[0].default_value * duty_assignment[[x for x in self.list_of_physicians if x.id == wish.user_id][0], [x for x in self.planning_period.duties_of_planning_period if x.id == wish.duty_team_duty_id][0]]

        # of shifts
        for wish in weekly_team_duty_wishes:
            if len([x for x in self.planning_period.team_duties_of_planning_period if x.id == wish.duty_team_duty_id]) > 0:
                objective += self.session.query(WeeklyBlockSpecificPreferences).filter_by(id=wish.weekly_block_specific_preference).all()[0].default_value * shift_assignment[[x for x in self.list_of_physicians if x.id == wish.user_id][0], [x for x in self.planning_period.team_duties_of_planning_period if x.id == wish.duty_team_duty_id][0]]


        # fair distribution in each pool
        objective -= mip.xsum(mip.xsum(
            pool.objective_weight * deviation_duties_pool_pos[pool, phy] + pool.objective_weight * deviation_duties_pool_neg[pool, phy]
            for phy in [x for x in self.list_of_physicians if x.id in [a.physician_id for a in pool.physicians_that_have_pool]])
                                for pool in self.pools if pool.fair_distribution)


        m.objective = objective

        #################################################################
        # SOLVE THE MIP ##################################################
        #################################################################

        print('Start solving the MIP after %s seconds.' % (time.time() - start_time))

        m.max_mip_gap = 0.03
        status = m.optimize()

        # proceed to the corresponding status of the MIP
        self.exit_status = "found solution"

        if status.value == 2:
            print('Problem is unbounded.')
            self.exit_status = "unbounded"

        if status.value == 1:
            print('Problem is infeasible.')
            self.exit_status = "infeasible"

        if status.value == 0 or status.value == 3:
            print('The objective value is %g.' % m.objective_value)

        return duty_assignment, shift_assignment
