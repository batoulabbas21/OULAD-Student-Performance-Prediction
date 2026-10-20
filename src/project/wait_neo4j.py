"""Wait for the lab Neo4j protocol, not just its container's running state."""
import os
import time
from neo4j import GraphDatabase
from neo4j.exceptions import AuthError, ServiceUnavailable, SessionExpired


def wait_ready(probe, timeout=90, interval=2, clock=time.monotonic, pause=time.sleep):
    deadline = clock() + timeout
    while True:
        try:
            probe()
            return
        except AuthError as exc:
            raise RuntimeError('Neo4j credentials were rejected. Use the existing NEO4J_USER/NEO4J_PASSWORD; do not reset its volume.') from exc
        except (ServiceUnavailable, SessionExpired) as exc:
            remaining = deadline - clock()
            if remaining <= 0:
                raise RuntimeError('Neo4j did not accept connections within the readiness timeout. Check its container logs and NEO4J_URI.') from exc
            pause(min(interval, remaining))


def main():
    uri = os.getenv('NEO4J_URI', 'bolt://localhost:7687')
    auth = (os.getenv('NEO4J_USER', 'neo4j'), os.getenv('NEO4J_PASSWORD', 'kr-labs-pw'))
    print('Waiting for Neo4j to accept authenticated Bolt connections...', flush=True)
    with GraphDatabase.driver(uri, auth=auth, connection_timeout=3, connection_acquisition_timeout=5) as driver:
        wait_ready(driver.verify_connectivity)
    print('Neo4j is ready.', flush=True)


if __name__ == '__main__':
    main()
