import os
from django.conf import settings
from game.models.game_log import GameLog, LogType
from unittest.mock import Mock

CLI_SKIP_LOGS = False

def set_cli_skip_logs(value):
    global CLI_SKIP_LOGS
    CLI_SKIP_LOGS = value

class LoggingTestMixin:
    """
    Mixin for Django TestCase to provide helper methods for asserting game logs.
    Can be disabled by setting ROOT_SKIP_LOG_TESTS=1 in the environment
    or by using the --skip-logs CLI flag.
    """

    @property
    def skip_log_tests(self):
        return CLI_SKIP_LOGS or os.getenv('ROOT_SKIP_LOG_TESTS', '0') == '1'

    def assertLogExists(self, log_type, player=None, parent=None, **details_subset):
        """
        Asserts that a log of the given type exists.
        If player is provided, asserts the log belongs to that player.
        If details_subset is provided, asserts those keys exist in the details JSON.
        """
        if self.skip_log_tests:
            return

        query = GameLog.objects.filter(log_type=log_type)
        if player:
            query = query.filter(player=player)
        if parent:
            query = query.filter(parent=parent)

        logs = list(query)
        
        found = False
        for log in logs:
            match = True
            for key, value in details_subset.items():
                if log.details.get(key) != value:
                    match = False
                    break
            if match:
                found = True
                break
        
        if not found:
            details_str = f" with details {details_subset}" if details_subset else ""
            player_str = f" for player {player}" if player else ""
            raise AssertionError(f"Log of type {log_type}{player_str}{details_str} not found. Existing logs: {[ (l.log_type, l.details) for l in GameLog.objects.all()]}")

    def assertLogCount(self, count, log_type=None, player=None):
        """Asserts the total number of logs matching the criteria."""
        if self.skip_log_tests:
            return

        query = GameLog.objects.all()
        if log_type:
            query = query.filter(log_type=log_type)
        if player:
            query = query.filter(player=player)
        
        actual_count = query.count()
        if actual_count != count:
            raise AssertionError(f"Expected {count} logs, found {actual_count}. Logs: {[ (l.log_type, l.details) for l in query ]}")

    def assertLogVisible(self, log, viewer_player, expected_details_subset):
        """
        Verifies that a log, when serialized for a specific viewer, contains certain details.
        This tests the redaction logic (Public vs Private views).
        """
        if self.skip_log_tests:
            return

        from game.serializers.logs.main import GameLogSerializer
        
        # Mock a request object with the viewer player's user
        request = Mock()
        request.user = viewer_player.user if viewer_player else None
        
        serializer = GameLogSerializer(log, context={"request": request})
        data = serializer.data['details']
        
        for key, value in expected_details_subset.items():
            actual_value = data.get(key)
            if actual_value != value:
                raise AssertionError(f"Redaction/Visibility mismatch for log {log.id} (type {log.log_type}). Expected {key}={value}, got {actual_value} for player {viewer_player}")
