from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Boolean, Float, Date, Time
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
import datetime

# Base class for models
Base = declarative_base()


class ReprMixin:
    def __repr__(self):
        pk = getattr(self, "id", None)
        if pk is not None:
            return f"<{self.__class__.__name__} {pk}>"
        return f"<{self.__class__.__name__}>"


class Institution(Base, ReprMixin):
    __tablename__ = 'institution'
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)
    license_expired = Column(DateTime, nullable=False, default=datetime.date(9999, 12, 31))
    members_of_institution = relationship("User", backref="institution_members", lazy=True)
    pools_of_institution = relationship("Pool", backref="institution_pools", lazy=True)
    qualifications_of_institution = relationship("Qualification", backref="institution_qualifications", lazy=True)
    physician_qualifications_of_institution = relationship("PhysicianQualification", backref="institution_physician_qualifications", lazy=True)
    duty_types_of_institution = relationship("DutyType", backref="institution_duty_types", lazy=True)
    duty_block_types_of_institution = relationship("DutyBlockType", backref="institution_duty_block_types", lazy=True)
    duty_block_type_assignments_of_institution = relationship("DutyBlockTypeAssignment", backref="institution_duty_block_type_assignments", lazy=True)


class User(Base, ReprMixin):
    __tablename__ = 'user'
    id = Column(Integer, primary_key=True)
    email = Column(String, unique=True, nullable=False)
    password = Column(String(60), nullable=False)
    institution_id = Column(Integer, ForeignKey("institution.id"), nullable=False)
    first_name = Column(String(60), nullable=False)
    last_name = Column(String(60), nullable=False)
    role = Column(String(60), nullable=False)
    beschaeftigungsumfang = Column(Float, nullable=False)
    planned_manually = Column(Boolean, nullable=False)
    is_being_planned = Column(Boolean, nullable=False)
    data_protection_agreement = Column(Boolean, nullable=False, default=False)
    is_active = Column(Boolean, nullable=False, default=True)
    qualifications_of_physician = relationship("PhysicianQualification", backref="qualifications_of_physician", cascade="all,delete", lazy=True)
    pools_of_physician = relationship("PhysicianPool", backref="pools_of_physician", cascade="all,delete", lazy=True)
    stations_of_physician = relationship("PhysicianStation", backref="stations_of_physician", cascade="all,delete", lazy=True)
    deactivations_of_physician = relationship("DeactivateUser", backref="deactivation_dates_of_physician", cascade="all,delete", lazy=True)
    duty_preferences_of_user = relationship("DutyPhysicianPreferences", backref="assignment_of_user", lazy=True, cascade="all,delete")
    team_duty_preferences_of_user = relationship("TeamDutyPhysicianPreferences", backref="team_duty_preferences_of_user", lazy=True, cascade="all,delete")
    duty_assignments = relationship("DutyPhysicianAssignment", backref="duty_assignments", lazy=True, cascade="all,delete")
    team_duty_assignments = relationship("TeamDutyPhysicianAssignment", backref="team_duty_assignments", lazy=True, cascade="all,delete")
    weekend_preferences = relationship("PhysicianPreferencesWeekend", backref="weekend_preferences", lazy=True, cascade="all,delete")

    def __repr__(self):
        return f"User('{self.id}', '{self.email}', '{self.first_name}', '{self.last_name}')"


class DeactivateUser(Base, ReprMixin):
    __tablename__ = 'deactivate_user'
    id = Column(Integer, primary_key=True)
    physician_id = Column(Integer, ForeignKey("user.id"), nullable=False)
    date_from = Column(Date, nullable=False, default=datetime.date.today())
    date_to = Column(Date, nullable=False, default=datetime.date.today() + datetime.timedelta(1))


class Qualification(Base, ReprMixin):
    __tablename__ = 'qualification'
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=False, nullable=False)
    institution_id = Column(Integer, ForeignKey("institution.id"), nullable=False)
    physicians_that_have_qualification = relationship("PhysicianQualification", backref="physicians_that_have_qualification", cascade="all,delete", lazy=True)
    duty_types_that_require_qualification = relationship("DutyQualificationType", backref="duty_types_that_require_qualification", cascade="all,delete", lazy=True)
    duties_that_require_qualification = relationship("DutyQualification", backref="qualifications_required_for_duties", lazy=True, cascade="all,delete")
    team_duties_that_require_qualification = relationship("TeamDutyQualification", backref="team_duties_that_require_qualification", lazy=True, cascade="all,delete")


class PhysicianQualification(Base, ReprMixin):
    __tablename__ = 'physician_qualification'
    id = Column(Integer, primary_key=True)
    institution_id = Column(Integer, ForeignKey("institution.id"), nullable=False)
    physician_id = Column(Integer, ForeignKey("user.id"), nullable=False)
    qualification_id = Column(Integer, ForeignKey("qualification.id"), nullable=False)
    date_from = Column(Date, nullable=False, default=datetime.date(1970, 1, 1))
    date_to = Column(Date, nullable=False, default=datetime.date(9999, 12, 31))


class Pool(Base, ReprMixin):
    __tablename__ = 'pool'
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=False, nullable=False)
    fair_distribution = Column(Boolean, unique=False, nullable=False)
    objective_weight = Column(Float, unique=False, default=1.0)
    maximal_number_of_duties = Column(Integer, unique=False, nullable=True)
    maximal_number_of_duties_soft = Column(Boolean, unique=False, nullable=False)
    weight_maximal_number_of_duties = Column(Integer, unique=False, nullable=True)
    minimal_number_of_duties = Column(Integer, unique=False, nullable=True)
    minimal_number_of_duties_soft = Column(Boolean, unique=False, nullable=False)
    weight_minimal_number_of_duties = Column(Integer, unique=False, nullable=True)
    exact_number_of_duties_per_month = Column(Integer, unique=False, nullable=True)
    maximal_number_of_physicians = Column(Integer, unique=False, nullable=True)
    maximal_number_of_physicians_soft = Column(Boolean, unique=False, nullable=True)
    weight_maximal_number_of_physicians = Column(Integer, unique=False, nullable=True)
    institution_id = Column(Integer, ForeignKey("institution.id"), nullable=False)
    physicians_that_have_pool = relationship("PhysicianPool", backref="physicians_that_have_pool", cascade="all,delete", lazy=True)
    duty_type_of_pool = relationship("PoolDutyTypeAssignment", backref="duty_type_of_pool", cascade="all,delete")


class PhysicianPool(Base, ReprMixin):
    __tablename__ = 'physician_pool'
    id = Column(Integer, primary_key=True)
    institution_id = Column(Integer, ForeignKey("institution.id"), nullable=False)
    physician_id = Column(Integer, ForeignKey("user.id"), nullable=False)
    pool_id = Column(Integer, ForeignKey("pool.id"), nullable=False)
    date_from = Column(Date, nullable=False, default=datetime.date(1970, 1, 1))
    date_to = Column(Date, nullable=False, default=datetime.date(9999, 12, 31))


class PoolDutyTypeAssignment(Base, ReprMixin):
    __tablename__ = 'pool_duty_type_assignment'
    id = Column(Integer, primary_key=True)
    pool_id = Column(Integer, ForeignKey("pool.id"), nullable=False)
    duty_type_id = Column(Integer, ForeignKey("duty_type.id"), nullable=False)
    holidays = Column(Boolean, default=False)


class Station(Base, ReprMixin):
    __tablename__ = 'station'
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=False, nullable=False)
    date_from = Column(Date, nullable=True, default=None)
    date_to = Column(Date, nullable=True, default=None)
    institution_id = Column(Integer, ForeignKey("institution.id"), nullable=False)
    physicians_that_have_station = relationship("PhysicianStation", backref="physicians_that_have_station", cascade="all,delete", lazy=True)


class PhysicianStation(Base, ReprMixin):
    __tablename__ = 'physician_station'
    id = Column(Integer, primary_key=True)
    institution_id = Column(Integer, ForeignKey("institution.id"), nullable=False)
    physician_id = Column(Integer, ForeignKey("user.id"), nullable=False)
    station_id = Column(Integer, ForeignKey("station.id"), nullable=False)
    date_from = Column(Date, nullable=False, default=datetime.date(1970, 1, 1))
    date_to = Column(Date, nullable=False, default=datetime.date(9999, 12, 31))


class Weekend(Base, ReprMixin):
    __tablename__ = 'weekend'
    id = Column(Integer, primary_key=True)
    start_time = Column(Time, nullable=False, default=datetime.time(hour=21))
    end_time = Column(Time, nullable=False, default=datetime.time(hour=5))
    min_free_weekends_per_month = Column(Integer, nullable=False, default=0)
    min_free_weekends_per_month_soft = Column(Boolean, nullable=False, default=True)
    min_free_weekends_per_month_weight = Column(Integer, nullable=False, default=0)
    max_number_weekends_per_month = Column(Integer, nullable=False, default=5)
    max_number_weekends_per_month_soft = Column(Boolean, nullable=False, default=True)
    max_number_weekends_per_month_weight = Column(Integer, nullable=False, default=0)
    max_consecutive_weekends = Column(Integer, nullable=True)


class DutyDutyRestingTime(Base, ReprMixin):
    __tablename__ = 'duty_duty_resting_time'
    id = Column(Integer, primary_key=True)
    duty_type_id = Column(Integer, ForeignKey("duty_type.id"), nullable=False)
    following_duty_type_id = Column(Integer, ForeignKey("duty_type.id"), nullable=False)
    # duty_type = relationship("DutyType", foreign_keys=[duty_type_id], backref='duty_duty_resting_times')
    # following_duty_type = relationship("DutyType", foreign_keys=[following_duty_type_id], backref='following_duty_duty_resting_times')
    resting_time_hard = Column(Float, nullable=False, default=0)
    resting_time_desired = Column(Float, nullable=False, default=0)
    weight_resting_time = Column(Float, nullable=False, default=0)


class DutyTeamDutyRestingTime(Base, ReprMixin):
    __tablename__ = 'duty_team_duty_resting_time'
    id = Column(Integer, primary_key=True)
    duty_type_id = Column(Integer, ForeignKey("duty_type.id"), nullable=False)
    resting_time_hard = Column(Float, nullable=False, default=0)
    resting_time_desired = Column(Float, nullable=False, default=0)
    weight_resting_time = Column(Float, nullable=False, default=0)


class TeamDutyRestingTime(Base, ReprMixin):
    __tablename__ = 'team_duty_resting_time'
    id = Column(Integer, primary_key=True)
    team_type_id = Column(Integer, ForeignKey("team_type.id"), nullable=False)
    resting_time_hard = Column(Float, nullable=False, default=0)
    resting_time_desired = Column(Float, nullable=False, default=0)
    weight_resting_time = Column(Float, nullable=False, default=0)
    resting_time_hard_team = Column(Float, nullable=False, default=0)
    resting_time_desired_team = Column(Float, nullable=False, default=0)
    weight_resting_time_team = Column(Float, nullable=False, default=0)


class DutyType(Base, ReprMixin):
    __tablename__ = 'duty_type'
    id = Column(Integer, primary_key=True)
    institution_id = Column(Integer, ForeignKey("institution.id"), nullable=False)
    name = Column(String, unique=False, nullable=False)
    time_start = Column(Time, nullable=False)
    time_end = Column(Time, nullable=False)
    monday = Column(Boolean, nullable=False)
    tuesday = Column(Boolean, nullable=False)
    wednesday = Column(Boolean, nullable=False)
    thursday = Column(Boolean, nullable=False)
    friday = Column(Boolean, nullable=False)
    saturday = Column(Boolean, nullable=False)
    sunday = Column(Boolean, nullable=False)
    on_holiday = Column(Boolean, nullable=False)
    time_start_on_holiday = Column(Time, nullable=True)
    time_end_on_holiday = Column(Time, nullable=True)
    before_holiday = Column(Boolean, nullable=False)
    time_start_before_holiday = Column(Time, nullable=True)
    time_end_before_holiday = Column(Time, nullable=True)
    after_holiday = Column(Boolean, nullable=False)
    time_start_after_holiday = Column(Time, nullable=True)
    time_end_after_holiday = Column(Time, nullable=True)
    only_on_holiday = Column(Boolean, nullable=False)
    only_before_holiday = Column(Boolean, nullable=False, default=False)  # Comment this out temporarily
    mandatory = Column(Boolean, nullable=False, default=True)
    weight_not_mandatory = Column(Float, nullable=True)
    automatically_create_as_single_duty = Column(Boolean, nullable=False, default=False)
    consecutive_assignment = Column(Boolean, nullable=False, default=True)
    weight_consecutive_assignment = Column(Integer, nullable=True, default=1)
    before_absence = Column(Boolean, default=True)
    after_absence = Column(Boolean, default=True)
    duty_block_type_assignments_of_duty_type = relationship("DutyBlockTypeAssignment", backref="duty_block_type_duty_block_assignments", lazy=True, cascade="all,delete")
    weekly_preference_assignments_to_duty_type = relationship("WeeklyPreferenceToDutyAssignment", backref="duty_type_to_weekly_preference_assignments", lazy=True, cascade="all,delete")
    duty_qualification_type_assignments_of_duty_type = relationship("DutyQualificationType", backref="duty_qualification_type_assignments", lazy=True, cascade="all,delete")
    duties_of_type = relationship("Duty", backref="duties_of_type", lazy=True, cascade="all,delete")
    pool_of_duty_type = relationship("PoolDutyTypeAssignment", backref="pool_of_duty_type", cascade="all,delete")
    resting_time_dtd = relationship("DutyTeamDutyRestingTime", backref="resting_time_dtd", lazy=True, cascade="all,delete")
    related_duty_duty_resting_times = relationship('DutyDutyRestingTime', foreign_keys=[DutyDutyRestingTime.duty_type_id], backref='related_duty_type', cascade="all,delete", overlaps="duty_duty_resting_times,duty_type")
    related_following_duty_duty_resting_times = relationship('DutyDutyRestingTime', foreign_keys=[DutyDutyRestingTime.following_duty_type_id], backref='related_following_duty_type', cascade="all,delete", overlaps="following_duty_duty_resting_times,following_duty_type")


class DutyQualificationType(Base, ReprMixin):
    __tablename__ = 'duty_qualification_type'
    id = Column(Integer, primary_key=True)
    institution_id = Column(Integer, ForeignKey("institution.id"), nullable=False)
    duty_type_id = Column(Integer, ForeignKey("duty_type.id"), nullable=False)
    qualification_id = Column(Integer, ForeignKey("qualification.id"), nullable=False)
    desired_value = Column(Boolean, nullable=False, default=True)
    is_soft = Column(Boolean, nullable=False, default=False)
    soft_weight = Column(Integer, nullable=True)


class DutyBlockType(Base, ReprMixin):
    __tablename__ = 'duty_block_type'
    id = Column(Integer, primary_key=True)
    institution_id = Column(Integer, ForeignKey("institution.id"), nullable=False)
    name = Column(String, unique=False, nullable=False)
    free_days_after_block = Column(Integer, nullable=False)
    other_duties_in_block_allowed = Column(Boolean, nullable=False, default=False)
    other_team_duties_in_block_allowed = Column(Boolean, nullable=False, default=False)
    blocks_of_duty_block_type = relationship("DutyBlock", backref="blocks_of_duty_block_type", lazy=True, cascade="all,delete")
    duty_block_type_assignments_of_duty_block_type = relationship("DutyBlockTypeAssignment", backref="duty_block_type_duty_block_type_assignments", lazy=True, cascade="all,delete")
    background_color = Column(String, nullable=True)


class DutyBlockTypeAssignment(Base, ReprMixin):
    __tablename__ = 'duty_block_type_assignment'
    id = Column(Integer, primary_key=True)
    institution_id = Column(Integer, ForeignKey("institution.id"), nullable=False)
    duty_block_type_id = Column(Integer, ForeignKey("duty_block_type.id"), nullable=False)
    order = Column(Integer)
    duty_type_id = Column(Integer, ForeignKey("duty_type.id"), nullable=False)
    weekday = Column(String, unique=False, nullable=False)


class WeeklyPreferenceToDutyAssignment(Base, ReprMixin):
    __tablename__ = 'weekly_preference_to_duty_assignment'
    id = Column(Integer, primary_key=True)
    weekly_pref_id = Column(Integer, ForeignKey("weekly_preference_blocks.id"), nullable=False)
    order = Column(Integer)
    duty_type_id = Column(Integer, ForeignKey("duty_type.id"), nullable=True)
    team_duty_id = Column(Integer, ForeignKey("team_duty.id"), nullable=True)
    weekday = Column(String, unique=False, nullable=False)


class TeamType(Base, ReprMixin):
    __tablename__ = 'team_type'
    id = Column(Integer, primary_key=True)
    institution_id = Column(Integer, ForeignKey("institution.id"), nullable=False)
    name = Column(String, unique=False, nullable=False)
    station_id = Column(Integer, ForeignKey("station.id"), nullable=True)
    time_start = Column(Time, nullable=False)
    time_end = Column(Time, nullable=False)
    monday = Column(Boolean, nullable=False)
    tuesday = Column(Boolean, nullable=False)
    wednesday = Column(Boolean, nullable=False)
    thursday = Column(Boolean, nullable=False)
    friday = Column(Boolean, nullable=False)
    saturday = Column(Boolean, nullable=False)
    sunday = Column(Boolean, nullable=False)
    on_holiday = Column(Boolean, nullable=False)
    time_start_on_holiday = Column(Time, nullable=True)
    time_end_on_holiday = Column(Time, nullable=True)
    before_holiday = Column(Boolean, nullable=False)
    time_start_before_holiday = Column(Time, nullable=True)
    time_end_before_holiday = Column(Time, nullable=True)
    after_holiday = Column(Boolean, nullable=False)
    time_start_after_holiday = Column(Time, nullable=True)
    time_end_after_holiday = Column(Time, nullable=True)
    only_on_holiday = Column(Boolean, nullable=False)
    number_of_required_physicians = Column(Integer, nullable=False)
    desired_number_of_physicians = Column(Integer, nullable=False)
    weight_of_occupation = Column(Integer, nullable=False)
    desired_number_of_physicians_2 = Column(Integer, nullable=True, default=0)
    weight_of_occupation_2 = Column(Integer, nullable=True, default=0)
    automatically_create_as_single_team = Column(Boolean, nullable=False, default=False)
    team_qualification_type_assignments_of_team_type = relationship("TeamQualificationType", backref="team_qualification_type_assignments_of_team_type", lazy=True, cascade="all,delete")
    team_block_type_assignments_of_team_type = relationship("TeamBlockTypeAssignment", backref="team_block_type_team_block_assignments", lazy=True, cascade="all,delete")
    team_duties_of_type = relationship("TeamDuty", backref="team_duties_of_type", lazy=True, cascade="all,delete")
    resting_time_tt = relationship("TeamDutyRestingTime", backref="resting_time_tt", lazy=True, cascade="all,delete")


class TeamBlockType(Base, ReprMixin):
    __tablename__ = 'team_block_type'
    id = Column(Integer, primary_key=True)
    institution_id = Column(Integer, ForeignKey("institution.id"), nullable=False)
    name = Column(String, unique=False, nullable=False)
    free_days_after_block = Column(Integer, nullable=True)
    other_duties_in_block_allowed = Column(Boolean, nullable=False, default=False)
    other_team_duties_in_block_allowed = Column(Boolean, nullable=False, default=False)
    consecutive_assignment = Column(Boolean, nullable=False, default=True)
    weight_consecutive_assignment = Column(Integer, nullable=True)
    blocks_of_team_block_type = relationship("TeamDutyBlock", backref="blocks_of_team_block_type", lazy=True, cascade="all,delete")
    team_block_type_assignments_of_team_block_type = relationship("TeamBlockTypeAssignment", backref="team_block_type_team_block_type_assignments", lazy=True, cascade="all,delete")
    consecutive_assignment_desired = Column(Boolean, default=False)
    maximal_consecutive_blocks = Column(Integer, nullable=True)
    maximal_consecutive_blocks_weight = Column(Integer, nullable=True)
    background_color = Column(String, nullable=True)


class TeamQualificationType(Base, ReprMixin):
    __tablename__ = 'team_qualification_type'
    id = Column(Integer, primary_key=True)
    institution_id = Column(Integer, ForeignKey("institution.id"), nullable=False)
    team_type_id = Column(Integer, ForeignKey("team_type.id"), nullable=False)
    qualification_id = Column(Integer, ForeignKey("qualification.id"), nullable=False)
    desired_value = Column(Boolean, nullable=False, default=True)
    is_soft = Column(Boolean, default=False)
    soft_weight = Column(Integer, nullable=True)


class TeamBlockTypeAssignment(Base, ReprMixin):
    __tablename__ = 'team_block_type_assignment'
    id = Column(Integer, primary_key=True)
    institution_id = Column(Integer, ForeignKey("institution.id"), nullable=False)
    team_block_type_id = Column(Integer, ForeignKey("team_block_type.id"), nullable=False)
    order = Column(Integer)
    team_type_id = Column(Integer, ForeignKey("team_type.id"), nullable=False)
    weekday = Column(String, unique=False, nullable=False)


class PlanningPeriod(Base, ReprMixin):
    __tablename__ = 'planning_period'
    id = Column(Integer, primary_key=True)
    institution_id = Column(Integer, ForeignKey("institution.id"), nullable=False)
    name = Column(String, unique=False, nullable=False)
    date_from = Column(Date, nullable=False)
    date_to = Column(Date, nullable=False)
    previous_planning_period_id = Column(Integer, ForeignKey("planning_period.id"), nullable=True)
    preferences_activated = Column(Boolean, nullable=False, default=False)
    deadline = Column(Date, nullable=True, default=None)
    published = Column(Boolean, nullable=False, default=False)
    date_generated = Column(Date, nullable=False)
    quality_before_plan = Column(Integer, unique=False, nullable=True)
    quality_after_plan = Column(Integer, unique=False, nullable=True)
    remarks = Column(String, unique=False, nullable=True)
    invisible = Column(Boolean, default=False)
    next_planning_period = relationship("PlanningPeriod", lazy=True, remote_side=[previous_planning_period_id])
    duties_of_planning_period = relationship("Duty", backref="planning_period_duties", lazy=True, cascade="all,delete")
    team_duties_of_planning_period = relationship("TeamDuty", backref="team_duties_of_planning_period", lazy=True, cascade="all,delete")
    planning_period_specific_day_options_preferences_configuration = relationship("PreferencesForDaysOptionsPlanningPeriodSpecific", backref="planning_period_specific_day_options_preferences_configuration", lazy=True, cascade="all,delete")
    planning_period_specific_general_preferences_configuration = relationship("GeneralPreferencesPlanningPeriodSpecific", backref="planning_period_specific_general_preferences_configuration", lazy=True, cascade="all,delete")
    duty_blocks_of_planning_period = relationship("DutyBlock", backref="planning_period_duty_blocks", lazy=True, cascade="all,delete")
    team_duty_blocks_of_planning_period = relationship("TeamDutyBlock", backref="team_duty_blocks_of_planning_period", lazy=True, cascade="all,delete")
    duty_preferences_of_planning_period = relationship("DutyPhysicianPreferences", backref="assignments_of_planning_period", lazy=True, cascade="all,delete")
    team_duty_preferences_of_planning_period = relationship("TeamDutyPhysicianPreferences", backref="team_duty_preferences_of_planning_period", lazy=True, cascade="all,delete")
    default_option_for_planning_period = relationship("DefaultValuePreferenceOptionsPlanningPeriodSpecific", backref="default_option_for_planning_period", lazy=True, cascade="all,delete")
    wekeend_preferences_for_planning_period = relationship("PhysicianPreferencesWeekend", backref="wekeend_preferences_for_planning_period", lazy=True, cascade="all,delete")
    assignments_of_planning_period = relationship("DutyPhysicianAssignment", backref="assignments_of_planning_period", lazy=True, cascade="all,delete")
    team_assignments_of_planning_period = relationship("TeamDutyPhysicianAssignment", backref="team_assignments_of_planning_period", lazy=True, cascade="all,delete")
    weekly_wishes_of_planning_period = relationship("WeeklyWishesOfPhysicians", backref="weekly_wishes_of_planning_period", lazy=True, cascade="all,delete")
    weekly_wishes_per_duty = relationship("WeeklyWishesOfPhysiciansPerDuty", backref="weekly_wishes_per_duty", lazy=True, cascade="all,delete")


class Duty(Base, ReprMixin):
    __tablename__ = 'duty'
    id = Column(Integer, primary_key=True)
    institution_id = Column(Integer, ForeignKey("institution.id"), nullable=False)
    name = Column(String, unique=False, nullable=False)
    time_start = Column(DateTime, nullable=False)
    time_end = Column(DateTime, nullable=False)
    mandatory = Column(Boolean, nullable=False, default=True)
    planning_period_id = Column(Integer, ForeignKey("planning_period.id"), nullable=False)
    duty_block_id = Column(Integer, ForeignKey("duty_block.id"), nullable=True)
    previous_duty = Column(Integer, nullable=True, unique=True)
    qualifications_of_duty = relationship("DutyQualification", backref="qualification_duties", lazy=True, cascade="all,delete")
    duty_preferences_of_duty = relationship("DutyPhysicianPreferences", backref="assignment_of_duty", lazy=True, cascade="all,delete")
    duty_assignment = relationship("DutyPhysicianAssignment", backref="duty_assignment", lazy=True, cascade="all,delete")
    duty_type = Column(Integer, ForeignKey("duty_type.id"), nullable=False)


class DutyBlock(Base, ReprMixin):
    __tablename__ = 'duty_block'
    id = Column(Integer, primary_key=True)
    institution_id = Column(Integer, ForeignKey("institution.id"), nullable=False)
    name = Column(String, unique=False, nullable=False)
    free_days_after_block = Column(Integer, nullable=False)
    other_duties_in_block_allowed = Column(Boolean, nullable=False, default=False)
    other_team_duties_in_block_allowed = Column(Boolean, nullable=False, default=False)
    type_of_duty_block = Column(Integer, ForeignKey("duty_block_type.id", name="n_type_of_duty_block"), nullable=False)
    planning_period_id = Column(Integer, ForeignKey("planning_period.id"), nullable=False)
    duties_of_duty_block = relationship("Duty", backref="assignment_duty_block", lazy=True, cascade="all,delete")


class DutyQualification(Base, ReprMixin):
    __tablename__ = 'duty_qualification'
    id = Column(Integer, primary_key=True)
    institution_id = Column(Integer, ForeignKey("institution.id"), nullable=False)
    duty_id = Column(Integer, ForeignKey("duty.id"), nullable=False)
    qualification_id = Column(Integer, ForeignKey("qualification.id"), nullable=False)
    desired_value = Column(Boolean, nullable=False, default=True)


class TeamDuty(Base, ReprMixin):
    __tablename__ = 'team_duty'
    id = Column(Integer, primary_key=True)
    institution_id = Column(Integer, ForeignKey("institution.id"), nullable=False)
    name = Column(String, unique=False, nullable=False)
    time_start = Column(DateTime, nullable=False)
    time_end = Column(DateTime, nullable=False)
    number_of_required_physicians = Column(Integer, nullable=False)
    desired_number_of_physicians = Column(Integer, nullable=False)
    weight_of_occupation = Column(Integer, nullable=False)
    planning_period_id = Column(Integer, ForeignKey("planning_period.id"), nullable=False)
    team_duty_block_id = Column(Integer, ForeignKey("team_duty_block.id"), nullable=True)
    qualifications_of_team_duty = relationship("TeamDutyQualification", backref="qualifications_of_team_duty", lazy=True, cascade="all,delete")
    team_duty_assignment = relationship("TeamDutyPhysicianAssignment", backref="team_duty_assignment", lazy=True, cascade="all,delete")
    team_duty_preferences_of_duty = relationship("TeamDutyPhysicianPreferences", backref="team_duty_preferences_of_duty", lazy=True, cascade="all,delete")
    team_type = Column(Integer, ForeignKey("team_type.id"), nullable=False)
    weekly_preference_assignments_to_team_duty_type = relationship("WeeklyPreferenceToDutyAssignment", backref="team_duty_to_weekly_preference_assignments", lazy=True, cascade="all,delete")


class TeamDutyBlock(Base, ReprMixin):
    __tablename__ = 'team_duty_block'
    id = Column(Integer, primary_key=True)
    institution_id = Column(Integer, ForeignKey("institution.id"), nullable=False)
    name = Column(String, unique=False, nullable=False)
    free_days_after_block = Column(Integer, nullable=False)
    other_duties_in_block_allowed = Column(Boolean, nullable=False, default=False)
    other_team_duties_in_block_allowed = Column(Boolean, nullable=False, default=False)
    previous_team_duty_block = Column(Integer, nullable=True, unique=True)
    team_block_type = Column(Integer, ForeignKey("team_block_type.id"), nullable=False)
    planning_period_id = Column(Integer, ForeignKey("planning_period.id"), nullable=False)
    team_duties_of_team_block = relationship("TeamDuty", backref="team_duties_of_team_block", lazy=True, cascade="all,delete")


class TeamDutyQualification(Base, ReprMixin):
    __tablename__ = 'team_duty_qualification'
    id = Column(Integer, primary_key=True)
    institution_id = Column(Integer, ForeignKey("institution.id"), nullable=False)
    team_duty_id = Column(Integer, ForeignKey("team_duty.id"), nullable=False)
    qualification_id = Column(Integer, ForeignKey("qualification.id"), nullable=False)
    desired_value = Column(Boolean, nullable=False, default=True)


class PreferencesForDaysOptionsConfiguration(Base, ReprMixin):
    __tablename__ = 'preferences_for_days_options_configuration'
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=False, nullable=False)
    default_description = Column(String, unique=False, nullable=False)
    default_value = Column(Float, unique=False, nullable=False)
    default_constrained = Column(Boolean, unique=False, nullable=False)
    default_constrained_value = Column(Float, unique=False, nullable=False)
    default_constrained_unit = Column(String, unique=False, nullable=False)
    default_option = relationship("DefaultValuePreferenceOptions", backref="default_option", lazy=True, cascade="all,delete")
    monday = Column(Boolean, default=True, nullable=False)
    tuesday = Column(Boolean, default=True, nullable=False)
    wednesday = Column(Boolean, default=True, nullable=False)
    thursday = Column(Boolean, default=True, nullable=False)
    friday = Column(Boolean, default=True, nullable=False)
    saturday = Column(Boolean, default=True, nullable=False)
    sunday = Column(Boolean, default=True, nullable=False)
    only_on_holiday = Column(Boolean, default=True, nullable=False)
    also_on_holiday = Column(Boolean, default=True, nullable=False)


class WeeklyPreferenceBlocks(Base, ReprMixin):
    __tablename__ = 'weekly_preference_blocks'
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=False, nullable=False)
    default_description = Column(String, unique=False, nullable=False)
    assignments_to_duty_type = relationship("WeeklyPreferenceToDutyAssignment", backref="preference_to_duty_types_assignments", lazy=True, cascade="all,delete")
    assignments_to_block_specific_preferences = relationship("WeeklyPreferencesToBlockAssignment", backref="assignments_to_block_specific_preferences", lazy=True, cascade="all,delete")
    weekly_wishes_of_physicians = relationship("WeeklyWishesOfPhysicians", backref="weekly_wishes_of_physicians", lazy=True, cascade="all,delete")


class WeeklyBlockSpecificPreferences(Base, ReprMixin):
    __tablename__ = 'weekly_block_specific_preferences'
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=False, nullable=False)
    default_value = Column(Float, unique=False, nullable=False)
    default_constrained = Column(Boolean, unique=False, nullable=False)
    default_constrained_value = Column(Float, unique=False, nullable=False)
    assignments_to_weekly_preference_blocks = relationship("WeeklyPreferencesToBlockAssignment", backref="assignments_to_weekly_preference_blocks", lazy=True, cascade="all,delete")
    weekly_prefs_of_physicians = relationship("WeeklyWishesOfPhysicians", backref="weekly_prefs_of_physicians", lazy=True, cascade="all,delete")
    weekly_prefs_per_duty = relationship("WeeklyWishesOfPhysiciansPerDuty", backref="weekly_prefs_per_duty", lazy=True, cascade="all,delete")


class WeeklyPreferencesToBlockAssignment(Base, ReprMixin):
    __tablename__ = 'weekly_preferences_to_block_assignment'
    id = Column(Integer, primary_key=True)
    weekly_pref_id = Column(Integer, ForeignKey("weekly_preference_blocks.id"), nullable=False)
    block_specific_pref_id = Column(Integer, ForeignKey("weekly_block_specific_preferences.id"), nullable=False)


class WeeklyWishesOfPhysicians(Base, ReprMixin):
    __tablename__ = 'weekly_wishes_of_physicians'
    id = Column(Integer, primary_key=True)
    planning_period_id = Column(Integer, ForeignKey("planning_period.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("user.id"), nullable=False)
    first_day_of_week = Column(Date)
    weekly_pref_block_id = Column(Integer, ForeignKey("weekly_preference_blocks.id"), nullable=False)
    weekly_block_specific_preference = Column(Integer, ForeignKey("weekly_block_specific_preferences.id"), nullable=False)


class WeeklyWishesOfPhysiciansPerDuty(Base, ReprMixin):
    __tablename__ = 'weekly_wishes_of_physicians_per_duty'
    id = Column(Integer, primary_key=True)
    planning_period_id = Column(Integer, ForeignKey("planning_period.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("user.id"), nullable=False)
    duty_team_duty_id = Column(Integer, nullable=False)
    is_duty = Column(Boolean, nullable=True)
    is_team_duty = Column(Boolean, nullable=True)
    weekly_block_specific_preference = Column(Integer, ForeignKey("weekly_block_specific_preferences.id"), nullable=False)


class DaysForDutySpecificPreferences(Base, ReprMixin):
    __tablename__ = 'days_for_duty_specific_preferences'
    id = Column(Integer, primary_key=True)
    monday = Column(Boolean, default=True, nullable=False)
    tuesday = Column(Boolean, default=True, nullable=False)
    wednesday = Column(Boolean, default=True, nullable=False)
    thursday = Column(Boolean, default=True, nullable=False)
    friday = Column(Boolean, default=True, nullable=False)
    saturday = Column(Boolean, default=True, nullable=False)
    sunday = Column(Boolean, default=True, nullable=False)
    weekend = Column(Boolean, default=True, nullable=False)
    only_on_holiday = Column(Boolean, default=True, nullable=False)
    also_on_holiday = Column(Boolean, default=True, nullable=False)
    additionally_on_holiday = Column(Boolean, default=True, nullable=False)


class GeneralPreferencesConfiguration(Base, ReprMixin):
    __tablename__ = 'general_preferences_configuration'
    id = Column(Integer, primary_key=True)
    two_days_on_weekend_preference_allowed = Column(Boolean, unique=False, nullable=False, default=True)
    two_days_on_weekend_preference_value = Column(Float, unique=False, nullable=False, default=0)
    only_planner_chooses_absences = Column(Boolean, nullable=False, default=False)
    duty_absences_allowed = Column(Boolean, nullable=False, default=False)
    max_duty_absences = Column(Integer, nullable=True)
    monday = Column(Boolean, default=True, nullable=False)
    tuesday = Column(Boolean, default=True, nullable=False)
    wednesday = Column(Boolean, default=True, nullable=False)
    thursday = Column(Boolean, default=True, nullable=False)
    friday = Column(Boolean, default=True, nullable=False)
    saturday = Column(Boolean, default=True, nullable=False)
    sunday = Column(Boolean, default=True, nullable=False)
    weekend = Column(Boolean, default=True, nullable=False)
    only_on_holiday = Column(Boolean, default=True, nullable=False)
    also_on_holiday = Column(Boolean, default=True, nullable=False)
    additionally_on_holiday = Column(Boolean, default=True, nullable=False)
    hide_block_duty_wishes = Column(Boolean, nullable=False, default=False)


class PreferencesForDaysOptionsPlanningPeriodSpecific(Base, ReprMixin):
    __tablename__ = 'preferences_for_days_options_planning_period_specific'
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=False, nullable=False)
    description = Column(String, unique=False, nullable=False)
    value = Column(Float, unique=False, nullable=False)
    constrained = Column(Boolean, unique=False, nullable=False)
    constrained_value = Column(Float, unique=False, nullable=False)
    constrained_unit = Column(String, unique=False, nullable=False)
    planning_period_id = Column(Integer, ForeignKey("planning_period.id"), nullable=False)
    default_option = relationship("DefaultValuePreferenceOptionsPlanningPeriodSpecific", backref="default_option", lazy=True, cascade="all,delete")
    monday = Column(Boolean, default=True, nullable=False)
    tuesday = Column(Boolean, default=True, nullable=False)
    wednesday = Column(Boolean, default=True, nullable=False)
    thursday = Column(Boolean, default=True, nullable=False)
    friday = Column(Boolean, default=True, nullable=False)
    saturday = Column(Boolean, default=True, nullable=False)
    sunday = Column(Boolean, default=True, nullable=False)
    weekend = Column(Boolean, default=True, nullable=False)
    only_on_holiday = Column(Boolean, default=True, nullable=False)
    also_on_holiday = Column(Boolean, default=True, nullable=False)


class DefaultValuePreferenceOptions(Base, ReprMixin):
    __tablename__ = 'default_value_preference_options'
    option_id = Column(Integer, ForeignKey("preferences_for_days_options_configuration.id"), nullable=False, primary_key=True)


class DefaultValuePreferenceOptionsPlanningPeriodSpecific(Base, ReprMixin):
    __tablename__ = 'default_value_preference_options_planning_period_specific'
    option_id = Column(Integer, ForeignKey("preferences_for_days_options_planning_period_specific.id"), nullable=False)
    planning_period_id = Column(Integer, ForeignKey("planning_period.id"), nullable=False, primary_key=True)


class GeneralPreferencesPlanningPeriodSpecific(Base, ReprMixin):
    __tablename__ = 'general_preferences_planning_period_specific'
    planning_period_id = Column(Integer, ForeignKey("planning_period.id"), nullable=False, primary_key=True)
    two_days_on_weekend_preference_allowed = Column(Boolean, unique=False, nullable=False)
    two_days_on_weekend_preference_value = Column(Float, unique=False, nullable=False)


class DutyPhysicianPreferences(Base, ReprMixin):
    __tablename__ = 'duty_physician_preferences'
    duty_id = Column(Integer, ForeignKey("duty.id"), nullable=False, primary_key=True)
    user_id = Column(Integer, ForeignKey("user.id"), nullable=False, primary_key=True)
    planning_period_id = Column(Integer, ForeignKey("planning_period.id"), nullable=False)
    preference = Column(Integer, unique=False, nullable=False)


class DutyAdditionalPhysicianAssignment(Base, ReprMixin):
    __tablename__ = 'duty_additional_physician_assignment'
    id = Column(Integer, primary_key=True)
    duty_id = Column(Integer, ForeignKey("duty.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("user.id"), nullable=False)
    planning_period_id = Column(Integer, ForeignKey("planning_period.id"), nullable=False)
    fixed_assignment = Column(Boolean, nullable=False, default=False)
    # Add relationship to Duty model
    duty = relationship("Duty", lazy=True)
    user = relationship("User", lazy=True)


class TeamDutyPhysicianPreferences(Base, ReprMixin):
    __tablename__ = 'team_duty_physician_preferences'
    team_duty_id = Column(Integer, ForeignKey("team_duty.id"), nullable=False, primary_key=True)
    user_id = Column(Integer, ForeignKey("user.id"), nullable=False, primary_key=True)
    planning_period_id = Column(Integer, ForeignKey("planning_period.id"), nullable=False)
    preference = Column(Integer, unique=False, nullable=False)


class AbsencePhysicians(Base, ReprMixin):
    __tablename__ = 'absence_physicians'
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("user.id"))
    day = Column(Date)


class DutyAbsences(Base, ReprMixin):
    __tablename__ = 'duty_absences'
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("user.id"))
    duty_id = Column(Integer, ForeignKey("duty.id"))


class TeamDutyAbsences(Base, ReprMixin):
    __tablename__ = 'team_duty_absences'
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("user.id"))
    team_duty_id = Column(Integer, ForeignKey("duty.id"))


class DutyPhysicianAssignment(Base, ReprMixin):
    __tablename__ = 'duty_physician_assignment'
    duty_id = Column(Integer, ForeignKey("duty.id"), nullable=False, primary_key=True)
    user_id = Column(Integer, ForeignKey("user.id"), nullable=False)
    planning_period_id = Column(Integer, ForeignKey("planning_period.id"), nullable=False)
    fixed_assignment = Column(Boolean, nullable=False, default=False)


class TeamDutyPhysicianAssignment(Base, ReprMixin):
    __tablename__ = 'team_duty_physician_assignment'
    id = Column(Integer, primary_key=True)
    team_duty_id = Column(Integer, ForeignKey("team_duty.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("user.id"), nullable=False)
    planning_period_id = Column(Integer, ForeignKey("planning_period.id"), nullable=False)
    fixed_assignment = Column(Boolean, nullable=False, default=False)


class PhysicianPreferencesWeekend(Base, ReprMixin):
    __tablename__ = 'physician_preferences_weekend'
    user_id = Column(Integer, ForeignKey("user.id"), nullable=False, primary_key=True)
    planning_period_id = Column(Integer, ForeignKey("planning_period.id"), nullable=False, primary_key=True)
    option = Column(String, unique=False, nullable=False)


class ApplicationSettings(Base, ReprMixin):
    __tablename__ = 'application_settings'
    id = Column(Integer, primary_key=True)
    bundesland = Column(String, unique=False, nullable=False, default="BY")
    mip_gap = Column(Float, unique=False, nullable=False, default=0)
