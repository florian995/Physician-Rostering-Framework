from database import get_session, clinic
from models import PlanningPeriod, DutyPhysicianAssignment, DutyAdditionalPhysicianAssignment, TeamDutyPhysicianAssignment
import ipSolver

# Create session
session = get_session()

def optimize_planning_period(planning_period_id):
    """Executes the optimization for a given planning period."""
    pp = session.get(PlanningPeriod, planning_period_id)

    if not pp:
        print(f"Planning Period with ID {planning_period_id} not found.")
        return

    input_data = {"planning_period": pp}

    # --- Run solver ---
    solver = ipSolver.ipSolver(input_data, session=session)  # pass session explicitly
    duty_assignment, team_duty_assignment = solver.solve()

    # --- Remove old duty assignments ---
    session.query(DutyPhysicianAssignment).filter(
        DutyPhysicianAssignment.duty_id.in_([d.id for d in pp.duties_of_planning_period]),
        DutyPhysicianAssignment.fixed_assignment == 0
    ).delete(synchronize_session=False)
    session.commit()

    # --- Assign new duties ---
    for d in pp.duties_of_planning_period:
        for p in solver.list_of_physicians:
            if duty_assignment[p, d].x is not None and duty_assignment[p, d].x >= 0.9:

                existing_assignment = session.query(DutyPhysicianAssignment).filter_by(
                    duty_id=d.id, user_id=p.id, planning_period_id=pp.id
                ).first()

                existing_additional_assignment = session.query(DutyAdditionalPhysicianAssignment).filter_by(
                    duty_id=d.id, user_id=p.id, planning_period_id=pp.id
                ).first()

                duty_has_assignment = session.query(DutyPhysicianAssignment).filter_by(duty_id=d.id).first()

                if existing_assignment is None and existing_additional_assignment is None:
                    if duty_has_assignment is None:
                        duty_physician_assignment = DutyPhysicianAssignment(
                            duty_id=d.id, user_id=p.id, planning_period_id=pp.id
                        )
                        session.add(duty_physician_assignment)
                    else:
                        duty_physician_assignment = DutyAdditionalPhysicianAssignment(
                            duty_id=d.id, user_id=p.id, planning_period_id=pp.id, fixed_assignment=False
                        )
                        session.add(duty_physician_assignment)

    session.commit()

    # --- Remove and reassign team duties ---
    session.query(TeamDutyPhysicianAssignment).filter(
        TeamDutyPhysicianAssignment.team_duty_id.in_([d.id for d in pp.team_duties_of_planning_period]),
        TeamDutyPhysicianAssignment.fixed_assignment == 0
    ).delete(synchronize_session=False)
    session.commit()

    for d in pp.team_duties_of_planning_period:
        for p in solver.list_of_physicians:
            if team_duty_assignment[p, d].x is not None and team_duty_assignment[p, d].x >= 0.9:
                existing_assignment = session.query(TeamDutyPhysicianAssignment).filter_by(
                    team_duty_id=d.id, user_id=p.id, planning_period_id=pp.id
                ).first()
                if existing_assignment is None:
                    team_duty_physician_assignment = TeamDutyPhysicianAssignment(
                        team_duty_id=d.id, user_id=p.id, planning_period_id=pp.id
                    )
                    session.add(team_duty_physician_assignment)

    session.commit()

    if solver.exit_status in ["infeasible", "unbounded"]:
        print(f"Optimization failed for Planning Period '{pp.name}': No feasible solution found.")
    else:
        print(f"Optimization successful for Planning Period '{pp.name}'.")

if __name__ == "__main__":
    if clinic == "card.db":
        period = session.query(PlanningPeriod).order_by(PlanningPeriod.id.desc()).first()
    else:
        period = session.query(PlanningPeriod).filter_by(name="Planungsperiode").first()

    optimize_planning_period(period.id)
    session.close()
