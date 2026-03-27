from django.test.runner import DiscoverRunner

class RootTestRunner(DiscoverRunner):
    """
    Custom test runner for Root project.
    Adds support for project-specific CLI flags.
    """
    
    def add_arguments(parser):
        DiscoverRunner.add_arguments(parser)
        parser.add_argument(
            '--skip-logs', 
            action='store_true',
            dest='skip_logs',
            help='Skip logging assertions in tests.'
        )

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.skip_logs = kwargs.get('skip_logs', False)
        
        # Propagate to the logging mixin's global state
        from game.tests.logging_mixin import set_cli_skip_logs
        set_cli_skip_logs(self.skip_logs)
