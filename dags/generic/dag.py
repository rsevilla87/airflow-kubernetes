import sys
import os
import logging
import yaml
from datetime import datetime
from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.operators.python_operator import PythonOperator
from airflow.config_templates.airflow_local_settings import LOG_FORMAT
from generic.util import var_loader

# Set Task Logger to INFO for better task logs
log = logging.getLogger("airflow.task")
handler = logging.StreamHandler(sys.stdout)
formatter = logging.Formatter(LOG_FORMAT)
handler.setLevel(logging.INFO)
handler.setFormatter(formatter)
log.addHandler(handler)


default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'email': ['airflow@example.com'],
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
}
root_dag_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# This Applies to all DAGs


def get_dags():
    dag_matrix = os.path.join(root_dag_dir, "dag_config", "dag_matrix.yml")
    with open(dag_matrix) as matrix:
        try:
            dags = yaml.safe_load(matrix)
        except yaml.YAMLError as err:
            print(err)
    return dags


def _load_tasks(task_file):
    task_file = os.path.join(root_dag_dir, "tasks", task_file)
    with open(task_file) as f:
        try:
            tasks = yaml.safe_load(f)
        except yaml.YAMLError as err:
            print(err)
    return tasks


def set_tasks(dag_name, tasks_files):
    def add_tasks(tasks, parent=None):
        for task in tasks:
            if "remote_script" in task:
                bash_command = f"curl -L {task['remote_script']} | bash"
            else:
                bash_command = f"{root_dag_dir}/scripts/{task['script']}"
            env = task.get("vars", {})
            # Get task variables from a nested dict within the dict dict
            # and override task variables from secret vars
            #env.update(var_loader.get_secret(dag_name).get(task['name'], {}))
            env.update(var_loader.get_secret(dag_name).get(task['name']))
            t = BashOperator(task_id=task['name'],
                             depends_on_past=False,
                             bash_command=bash_command,
                             retries=task.get("retries", 1),
                             trigger_rule=task.get('trigger_rule', 'all_success'),
                             start_date=datetime(2021, 1, 1),
                             env=env
                             )
            if parent:
                t.set_upstream(parent)
            if "sub_tasks" in task:
                add_tasks(task["sub_tasks"], t)
    for tf in tasks_files:
        tasks = _load_tasks(tf)
        add_tasks(tasks)


for dag_config in get_dags():
    with DAG(dag_id=dag_config['name'],
             schedule_interval=dag_config["scheduler"]["interval"],
             default_args=default_args,
             catchup=False,
             max_active_runs=1,
             start_date=datetime.now()) as dag:
        set_tasks(dag_config['name'], dag_config['tasks'])
        globals()[dag_config['name']] = dag
