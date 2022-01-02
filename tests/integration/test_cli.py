import unittest
import os
import warnings

import ecs_tunnel
from ecs_tunnel.cli import cli

import click.testing
from dotenv import load_dotenv


class TestCliInt(unittest.TestCase):

    def setUp(self) -> None:
        load_dotenv()
        warnings.simplefilter("ignore", ResourceWarning)

    def test_no_forwards(self):
        args = [
            '--cluster', os.environ['CLUSTER'],
            '--task', os.environ['TASK']
        ]

        cr = click.testing.CliRunner()

        result = cr.invoke(cli, args=args, catch_exceptions=False)
        print(result.stdout)

        self.assertIn('ERROR: no forwards (-L/-D) given', result.stdout)

    def test_local_forward_single(self):
        local_port = ecs_tunnel.EcsTunnel._get_port()

        args = [
            '--cluster', os.environ['CLUSTER'],
            '--task', os.environ['TASK'],
            '-L', f'{local_port}:localhost:8000'
        ]

        cr = click.testing.CliRunner()

        result = cr.invoke(cli, args=args, catch_exceptions=False)
        print(result.stdout)


if __name__ == '__main__':
    unittest.main()
