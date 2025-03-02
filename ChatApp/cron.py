from django_cron import CronJobBase, Schedule
from chat.models import GameRoom


class KickOutInactivePlayersCronJob(CronJobBase):
    RUN_EVERY_MINS = 1
    schedule = Schedule(run_every_mins=RUN_EVERY_MINS)
    code = 'chat.kick_out_inactive_players_cron_job'

    def do(self):
        # GameRoom.game_manager.kick_out_inactive_players()
        GameRoom.game_manager.stop_inactive_rooms()
