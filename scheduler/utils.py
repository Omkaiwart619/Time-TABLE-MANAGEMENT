from django.db import transaction
from .models import TimetableEntry

def move_timetable_entry(entry_id, new_day, new_period):
    try:
        new_period = int(new_period)

        with transaction.atomic():
            entry = TimetableEntry.objects.select_for_update().get(pk=entry_id)

            # Check if this subject is marked as a lab
            is_lab = getattr(entry.subject, 'is_lab', False)

            if is_lab:
                # Find the adjacent lab entry on the original day & batch
                # Labs are usually scheduled in consecutive periods (e.g. p and p+1, or p and p-1)
                sibling = TimetableEntry.objects.filter(
                    day=entry.day,
                    batch=entry.batch,
                    subject=entry.subject,
                    period__in=[entry.period - 1, entry.period + 1]
                ).exclude(pk=entry.pk).first()

                if sibling:
                    # Determine offset relative to the dragged entry
                    offset = sibling.period - entry.period
                    target_sibling_period = new_period + offset

                    # Prevent moving outside valid period bounds (1 to 7)
                    if not (1 <= target_sibling_period <= 7):
                        return False, "Cannot move lab block: resulting periods would fall outside schedule boundaries."

                    # Prevent target collision with lunch/break (Period 4)
                    if new_period == 4 or target_sibling_period == 4:
                        return False, "Cannot move lab block across Lunch/Break (Period 4)."

                    # Temporarily clear periods to avoid unique constraint collisions during update
                    orig_p1, orig_p2 = entry.period, sibling.period
                    entry.period = -1
                    sibling.period = -2
                    entry.save()
                    sibling.save()

                    # Save new slots together
                    entry.day = new_day
                    entry.period = new_period
                    entry.save()

                    sibling.day = new_day
                    sibling.period = target_sibling_period
                    sibling.save()

                    return True, "Lab block moved successfully."

            # Regular single-slot movement for theory
            if new_period == 4:
                return False, "Cannot assign classes to Lunch/Break (Period 4)."

            entry.day = new_day
            entry.period = new_period
            entry.save()
            return True, "Slot moved successfully."

    except TimetableEntry.DoesNotExist:
        return False, "Timetable entry not found."
    except Exception as e:
        return False, str(e)