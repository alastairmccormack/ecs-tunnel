# ECS Tunnel

Port forwarding for AWS ECS tasks. Hopefully filling a gap until AWS provide similar support natively.

### Features:

 - Forward local port to local port on task
 - Forward local port to a remote host/port accessible from task (Requires netcat. See _Prerequisites_)
 - HTTP Proxy (Requires ncat. See _Prerequisites_)
 
## Prerequisites

 - Python 3.8
 - AWS CLI 2.x - https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html
 - AWS Session Manager Plugin -
https://docs.aws.amazon.com/systems-manager/latest/userguide/session-manager-working-with-install-plugin.html
 
### Remote address:port Forwarding

 To forward a port to a remote address accessible from the running task, it's necessary to
install a version of netcat that supports `-e`. 

#### Alpine
On **Alpine** with Busybox shell (default), netcat
is already available.

#### Debian
| Netcat Version | Debian Package |
| ------ | -------- |
| Original Netcat | netcat-traditional |
| NMAP Ncat | ncat |

### HTTP Proxy

 - NMAP Ncat

| Debian Package | Alpine Package |
| ------ | -------- |
| ncat | nmap-ncat |

## Installation

`pip3 install ecs-tunnel`

## Usage

```
Usage: ecs-tunnel [OPTIONS]

Options:
  -c, --cluster CLUSTER_NAME      [required]
  -t, --task TASK_ID              [required]
  -n, --container CONTAINER_NAME  Container name. Required if task is running
                                  more than one container
  -L, --local LOCAL_PORT[:REMOTE_ADDR]:REMOTE_PORT
                                  Forward a local port to a remote
                                  address/port. Requires Busybox nc, netcat-
                                  traditional or NMAP Ncat installed (Netcat
                                  with support for "-e") on a given ECS task
  -H, --http-proxy PORT           Setup an HTTP(S) Proxy on given port.
                                  Requires NMAP Ncat installed on given ECS
                                  task
  --region AWS_REGION
  --profile AWS_PROFILE_NAME
  --aws-exec BIN                  aws command line executable. (default:
                                  "aws")
  --verbose
  --version                       Show the version and exit.
  --help                          Show this message and exit.
```

### Examples

Tunnel local port 8000 to port 8080 on the remote task:
```
ecs-tunnel -L 8000:8080 -c my-cluster -t 7e2c99a9c63eb1fc3949d9e966d91f3b
```

Tunnel local port 5432 to port 5432 on a remote host:
```
ecs-tunnel -L 5432:my-db-cluster:5432 -c my-cluster -t 7e2c99a9c63eb1fc3949d9e966d91f3b
```

Setup HTTP proxy on port 8888:
```
ecs-tunnel -D 8888 -c my-cluster -t 7e2c99a9c63eb1fc3949d9e966d91f3b
```


## But How?

Port forwarding to a port on an EC2 node is currently supported and documented using AWS Systems Manager,
 AWS Session Manager Plugin and the `aws session` command. 
By observing how `aws ecs execute-command` also used the AWS Session Manager, and taking insperation from SSH 
port forwarding, it was possible to write a quick wrapper that used the EC2 port forwarding profile with 
ECS tasks.

Unfortunately, the AWS Systems Manager doesn't seem to expose a way of forwading a local port to a remote
port via the connected task. Instead, we use compatible versions of netcat to provide similar functionality.

## Todo

- Check for remote netcat support
- Implement native Python session-manager using websockets 
