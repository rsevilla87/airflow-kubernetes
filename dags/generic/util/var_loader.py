from airflow.models import Variable

def get_secret(dag_name):
    return Variable.get(dag_name, deserialize_json=True, default_var={})
