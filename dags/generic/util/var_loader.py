from airflow.models import Variable


def get_secrets(secrets):
    env = {}
    for secret in secrets:
        env.update(Variable.get(secret, deserialize_json=True))
    return env
