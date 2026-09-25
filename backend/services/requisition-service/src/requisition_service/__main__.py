"""python -m requisition_service [--env-file PATH]"""

from teamora_common import run_service

from . import SERVICE, build_app

run_service(SERVICE, build_app)
