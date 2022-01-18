import errno
import json
import logging
import os
import random
import shutil
import socket
import typing

import boto3
import jmespath
import pexpect
import pexpect.exceptions


class EcsTunnelException(Exception):
    pass


class EcsTunnel:
    cluster_id: str
    task_id: str
    container_name: typing.Optional[str]
    aws_cli_exec: str

    def __init__(
            self,
            cluster_id: str,
            task_id: str,
            container_name: str = None,
            aws_cli_exec: str = 'aws',
            aws_access_key_id: str = None,
            aws_secret_access_key: str = None,
            aws_session_token: str = None,
            aws_region_name: str = None,
            aws_profile_name: str = None,

    ):
        self.cluster_id = cluster_id
        self.task_id = task_id
        self.container_name = container_name

        self.aws_cli_exec = aws_cli_exec

        self._logger = logging.getLogger('ecs_tunnel')

        self._boto3_session = boto3.Session(
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
            aws_session_token=aws_session_token,
            region_name=aws_region_name,
            profile_name=aws_profile_name
        )

        self._ecs_client = self._boto3_session.client('ecs')
        self._ssm_client = self._boto3_session.client('ssm')
        self._aws_access_key_id = aws_access_key_id
        self._aws_secret_access_key = aws_secret_access_key
        self._aws_session_token = aws_session_token
        self._aws_region_name = aws_region_name
        self._aws_profile_name = aws_profile_name

        self._ssm_target_id = self._get_task_id()

        self._port_fw_procs: typing.List[pexpect.spawn] = []
        self._ecs_exec_sessions: typing.List[dict] = []

        # See warning in https://docs.python.org/3/library/subprocess.html#popen-constructor
        self._resolved_aws_cli_exec = shutil.which(self.aws_cli_exec)

        if not self._resolved_aws_cli_exec:
            raise FileNotFoundError(self.aws_cli_exec)

    def _get_task_id(self):
        response = self._ecs_client.describe_tasks(
            cluster=self.cluster_id,
            tasks=[
                self.task_id,
            ]
        )

        if failure_reason := jmespath.search(f"failures[0].reason", response):
            raise EcsTunnelException(f'Task failure. Reason: {failure_reason}')

        if self.container_name:
            container_runtime_id = jmespath.search(
                f"tasks[0].containers[?name = '{self.container_name}'].runtimeId",
                response
            )
        else:
            container_runtime_id = jmespath.search(f"tasks[0].containers[0].runtimeId", response)

        if container_runtime_id is None:
            raise EcsTunnelException('Task runtime id could not be resolved')

        return f'ecs:{self.cluster_id}_{self.task_id}_{container_runtime_id}'

    def _get_env(self):
        aws_env = os.environ

        if self._aws_profile_name:
            aws_env['AWS_DEFAULT_PROFILE'] = self._aws_profile_name
        if self._aws_access_key_id:
            aws_env['AWS_ACCESS_KEY_ID'] = self._aws_access_key_id
        if self._aws_access_key_id:
            aws_env['AWS_SECRET_ACCESS_KEY'] = self._aws_secret_access_key
        if self._aws_session_token:
            aws_env['AWS_SESSION_TOKEN'] = self._aws_session_token
        if self._aws_region_name:
            aws_env['AWS_DEFAULT_REGION'] = self._aws_region_name

        return aws_env

    def _get_ssm_start_session_cmd(self, local_port: int, remote_port: int) -> typing.List[str]:

        parameters = {
            'portNumber': [
                str(remote_port)
            ],
            'localPortNumber': [
                str(local_port)
            ]
        }
        parameters_json = json.dumps(parameters)

        aws_cmd = [
            'ssm', 'start-session',
            '--target', self._ssm_target_id,
            '--document-name', 'AWS-StartPortForwardingSession',
            '--parameters', parameters_json
        ]

        return aws_cmd

    @classmethod
    def _get_port(cls, port: int = None, check_in_use=False) -> int:
        """ Try to find a random dynamic port to use as a local port """
        # If port is not set return a random dynamic port

        if port:
            return port

        candidate_port = random.randrange(1024, 49151)

        if check_in_use:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

            try:
                s.bind(('0.0.0.0', candidate_port))
                return candidate_port
            except socket.error as e:
                if e.errno == errno.EADDRINUSE:
                    return cls._get_port()
                else:
                    raise
        else:
            return candidate_port

    def local_port_tunnel(self, remote_port: int, local_port: int = None) -> int:
        """ Tunnel a local port to a local port on the remote instance

        :return the local port
        """

        local_port = self._get_port(local_port, check_in_use=True)

        aws_cmd = self._get_ssm_start_session_cmd(local_port=local_port, remote_port=remote_port)

        self._logger.debug(f'AWS CLI start session cmd: {self._resolved_aws_cli_exec} {" ".join(aws_cmd)}')

        child = pexpect.spawn(command=self._resolved_aws_cli_exec, args=aws_cmd, env=self._get_env())

        try:
            child.expect('Waiting for connections')
        except pexpect.exceptions.TIMEOUT:
            raise EcsTunnelException(f'AWS session-manager did not reach "Waiting for connections". '
                                     f'Stdout: {child.before}')

        self._logger.debug(f'Session started successfully (Pid: {child.pid})')

        self._logger.debug(f'{child.before=}')
        self._logger.debug(f'{child.after=}')

        self._port_fw_procs.append(child)

        self._logger.debug(f'Forwarding {local_port} to {self.task_id}:{remote_port}')

        return local_port

    def _run_remote_ecs_cmd(self, cmd: str):
        execute_command_args = {
            'cluster': self.cluster_id,
            'command': cmd,
            'interactive': True,
            'task': self.task_id
        }

        if self.container_name:
            execute_command_args['container'] = self.container_name

        exec_response = self._ecs_client.execute_command(**execute_command_args)

        self._ecs_exec_sessions.append(exec_response)
        self._logger.debug(f'Started ECS exec command: {exec_response}')

    def remote_port_tunnel(self, remote_port: int, remote_host: str, local_port: int = None):

        # A random port to proxy through
        # TODO: check in use
        proxy_port = self._get_port()

        netcat_cmd = f'nc -lk -p {proxy_port} -e nc {remote_host} {remote_port}'
        self._run_remote_ecs_cmd(cmd=netcat_cmd)

        return self.local_port_tunnel(local_port=local_port, remote_port=proxy_port)

    def http_proxy_port_tunnel(self, remote_port=None, local_port=None):
        remote_port = self._get_port(remote_port)
        local_port = self._get_port(local_port)

        ncat_cmd = f'ncat -l {remote_port} --proxy-type http'
        self._run_remote_ecs_cmd(cmd=ncat_cmd)

        return self.local_port_tunnel(local_port=local_port, remote_port=remote_port)

    def remote_port_tunnel_pexpect(self, remote_port: int, remote_host: str, local_port=None):

        aws_cmd = {
            'execute-command',
            '--cluster', self.cluster_id,
            '--command', '/usr/bin/bash',
            '--interactive',
            '--task', self.task_id
        }

        child = pexpect.spawn(command=self._resolved_aws_cli_exec, args=aws_cmd, env=self._get_env())

    def close(self):
        self._logger.debug('Trying to kill running exec sessions')
        for exec_session in self._ecs_exec_sessions:
            session_id = jmespath.search('session.sessionId', exec_session)
            if session_id:
                self._logger.debug(f'Terminating SSM session: {session_id}')
                self._ssm_client.terminate_session(SessionId=session_id)
        self._ecs_exec_sessions = []

        self._logger.debug('Trying to kill running session-managers')
        for proc in self._port_fw_procs:
            if proc.isalive():
                self._logger.debug(f'Killing AWS session-manager-plugin: {proc.pid}')
                proc.terminate()
        self._port_fw_procs = []

    def __del__(self):
        # noinspection PyBroadException
        try:
            self.close()
        except BaseException:
            pass
