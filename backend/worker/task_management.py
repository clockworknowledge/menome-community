import socket
import time
from kombu.exceptions import OperationalError
from celery import Celery
import logging
from celery.result import AsyncResult
from celery.exceptions import TimeoutError, CeleryError
from celery.app.control import Inspect

def create_celery_app(broker_url, result_backend, max_retries=5, wait_seconds=5):
    """
    Create and configure a Celery app, ensuring that the broker is available.

    Args:
        broker_url (str): URL of the message broker (e.g., RabbitMQ)
        result_backend (str): URL of the result backend
        max_retries (int): Maximum number of connection attempts
        wait_seconds (int): Wait time between retries

    Returns:
        Celery: Configured Celery app instance

    Raises:
        Exception: If unable to connect to the broker after max_retries
    """
    broker_connected = False
    for attempt in range(max_retries):
        try:
            # Debug: Check if the hostname can be resolved
            hostname = broker_url.split('@')[1].split(':')[0]
            logging.info(f"Resolving hostname: {hostname}")
            ip_address = socket.gethostbyname(hostname)
            logging.info(f"Resolved hostname {hostname} to {ip_address}")

            # Try to establish a connection to the broker
            celery_temp = Celery(broker=broker_url)
            celery_temp.connection(hostname=broker_url)
            celery_temp.connection().ensure_connection(max_retries=1)
            logging.info("Successfully connected to the broker!")
            broker_connected = True
            break
        except OperationalError as e:
            logging.warning(f"Broker connection failed on attempt {attempt + 1}/{max_retries}. Retrying in {wait_seconds} seconds... Error: {e}")
            time.sleep(wait_seconds)
        except socket.gaierror as e:
            logging.error(f"Hostname resolution failed: {e}")
            break
        except Exception as e:
            logging.error(f"Unexpected error: {e}")
            break

    if not broker_connected:
        logging.error("Failed to connect to the broker after several attempts. Celery task worker is offline.")

    # Create the Celery app regardless of the broker connection status
    celery_app = Celery("worker", broker=broker_url, backend=result_backend)
    celery_app.conf.task_routes = {"celery_worker.test_celery": "celery"}
    celery_app.conf.update(task_track_started=True)

    return celery_app


# Define a function to purge the Celery queue
def purge_celery_queue(celery_app):
    """
    Purge all tasks from the Celery queue.

    This function clears all pending tasks from all active queues in the Celery app.

    Args:
        celery_app (Celery): The Celery app instance to purge queues from.
    """
    i = Inspect(app=celery_app)
    active_queues = i.active_queues()
    if active_queues:
        for queue in active_queues.keys():
            celery_app.control.purge()

# Define a function to get the task info
def get_task_info(task_id: str):
    """
    Retrieve information about a specific Celery task.

    Args:
        task_id (str): The ID of the task to retrieve information for

    Returns:
        dict: A dictionary containing task information including status and result (if available)

    Raises:
        TimeoutError: If retrieving the task result times out
        CeleryError: For general Celery-related errors
        Exception: For any other unexpected errors
    """
    try:
        task = AsyncResult(task_id)

        # Task Not Ready
        if not task.ready():
            return {"task_id": str(task_id), "status": task.status}

        # Task done: return the value
        task_result = task.get(timeout=10)  # Set a timeout for task.get() if needed
        return {
            "task_id": str(task_id),
            "result": task_result,
            "status": task.status
        }

    except TimeoutError:
        # Handle timeout exceptions
        return {
            "task_id": str(task_id),
            "error": "Timeout while retrieving the task result",
            "status": "TIMEOUT"
        }

    except CeleryError as e:
        # Handle general Celery errors
        return {
            "task_id": str(task_id),
            "error": str(e),
            "status": "ERROR"
        }

    except Exception as e:
        # Handle other exceptions
        return {
            "task_id": str(task_id),
            "error": f"An error occurred: {e}",
            "status": "FAILURE"
        }
